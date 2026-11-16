#!/usr/bin/env python3
"""env-doctor: audit a .env file against its .env.example.

The problem it solves: every project has a .env.example listing the
variables the app needs, and every developer has a local .env that
slowly drifts out of sync -- a key is added to the example and nobody
updates their .env, a key is renamed, a value is left blank, a key is
pasted twice. The app then crashes at runtime with a confusing error
("KeyError: DATABASE_URL") instead of failing fast with a clear list.

env-doctor compares the two files and reports, in plain language:

* missing keys  -- in .env.example but not in .env
* extra keys    -- in .env but not in .env.example (stale / typo?)
* empty values  -- keys present but with no value
* duplicates    -- the same key defined twice (last one wins silently)
* malformed lines -- lines that are not KEY=VALUE at all

It can also generate a .env.example from a .env (--init, values
redacted) and append missing keys to a .env (--fix).

Standard library only. No network, no dependencies.

Usage:
    python env_doctor.py audit [--env .env] [--example .env.example]
    python env_doctor.py audit --json
    python env_doctor.py audit --strict        # extra keys also fail
    python env_doctor.py init [--env .env] [--example .env.example]
    python env_doctor.py fix  [--env .env] [--example .env.example]
    python env_doctor.py --help
"""

import argparse
import json
import re
import sys
from pathlib import Path

__version__ = "1.0.0"

_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class EnvFile:
    """Parsed representation of one .env-style file."""

    def __init__(self, path):
        self.path = Path(path)
        self.values = {}        # key -> value (last definition wins)
        self.first_seen = {}    # key -> first line number
        self.duplicates = {}    # key -> list of line numbers (all occurrences)
        self.malformed = []     # list of (line_no, raw_line)
        self._parse()

    def _parse(self):
        if not self.path.exists():
            raise FileNotFoundError(f"file not found: {self.path}")
        for lineno, raw in enumerate(self.path.read_text().splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            if "=" not in line:
                self.malformed.append((lineno, raw))
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if not _KEY_RE.match(key):
                self.malformed.append((lineno, raw))
                continue
            value = _unquote(_strip_inline_comment(value.strip()))
            if key in self.values:
                self.duplicates.setdefault(key, [self.first_seen[key]])
                self.duplicates[key].append(lineno)
            else:
                self.first_seen[key] = lineno
            self.values[key] = value

    def empty_keys(self):
        """Keys present with an empty value."""
        return sorted(k for k, v in self.values.items() if v == "")


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _strip_inline_comment(value):
    """Remove a trailing ' # comment' from an unquoted value.

    Quoted values keep their '#' characters; unquoted values treat
    ' #' (hash preceded by whitespace) as the start of a comment.
    """
    if value.startswith(("'", '"')):
        return value
    for sep in (" #", "\t#"):
        idx = value.find(sep)
        if idx != -1:
            return value[:idx].rstrip()
    return value


def audit(env_path, example_path):
    """Compare .env against .env.example; return a report dict."""
    env = EnvFile(env_path)
    example = EnvFile(example_path)
    missing = sorted(set(example.values) - set(env.values))
    extra = sorted(set(env.values) - set(example.values))
    return {
        "env": str(env_path),
        "example": str(example_path),
        "missing": missing,
        "extra": extra,
        "empty": env.empty_keys(),
        "duplicates": {k: v for k, v in sorted(env.duplicates.items())},
        "malformed": [{"line": n, "text": t} for n, t in env.malformed],
        "example_malformed": [{"line": n, "text": t}
                              for n, t in example.malformed],
        "env_keys": len(env.values),
        "example_keys": len(example.values),
    }


def audit_problems(report, strict=False):
    """True if the report contains anything that should fail a check."""
    if report["missing"] or report["empty"] or report["duplicates"]:
        return True
    if report["malformed"] or report["example_malformed"]:
        return True
    if strict and report["extra"]:
        return True
    return False


def format_report(report):
    """Human-readable one-screen summary of an audit report."""
    lines = [f"env-doctor: {report['env']} vs {report['example']}",
             f"  {report['env_keys']} keys in .env, "
             f"{report['example_keys']} keys in .env.example"]
    if report["missing"]:
        lines.append("  MISSING (needed, not set):")
        lines += [f"    - {k}" for k in report["missing"]]
    if report["empty"]:
        lines.append("  EMPTY (present, no value):")
        lines += [f"    - {k}" for k in report["empty"]]
    if report["extra"]:
        lines.append("  EXTRA (in .env, not in example):")
        lines += [f"    - {k}" for k in report["extra"]]
    if report["duplicates"]:
        lines.append("  DUPLICATES (defined more than once):")
        for k, where in report["duplicates"].items():
            lines.append(f"    - {k} (lines {', '.join(map(str, where))})")
    if report["malformed"]:
        lines.append("  MALFORMED LINES in .env:")
        for m in report["malformed"]:
            lines.append(f"    - line {m['line']}: {m['text']!r}")
    if report["example_malformed"]:
        lines.append("  MALFORMED LINES in .env.example:")
        for m in report["example_malformed"]:
            lines.append(f"    - line {m['line']}: {m['text']!r}")
    if not audit_problems(report):
        lines.append("  OK: .env matches .env.example")
    return "\n".join(lines)


def init_example(env_path, example_path):
    """Write a .env.example from a .env, with values redacted.

    Returns the list of keys written. Refuses to overwrite an existing
    example file unless it was itself generated by env-doctor.
    """
    env = EnvFile(env_path)
    example_path = Path(example_path)
    if example_path.exists():
        head = example_path.read_text().splitlines()[:1]
        if not head or "Generated by env-doctor" not in head[0]:
            raise FileExistsError(
                f"{example_path} already exists and was not generated "
                "by env-doctor; delete it first or pick another path")
    lines = ["# Generated by env-doctor -- fill in real values, "
             "do not commit secrets here"]
    lines += [f"{key}=" for key in sorted(env.values)]
    example_path.write_text("\n".join(lines) + "\n")
    return sorted(env.values)


def fix_env(env_path, example_path):
    """Append missing example keys (empty) to .env. Returns keys added."""
    env = EnvFile(env_path)
    example = EnvFile(example_path)
    missing = sorted(set(example.values) - set(env.values))
    if not missing:
        return []
    with open(env_path, "a") as fh:
        fh.write("\n# Added by env-doctor -- fill in values\n")
        for key in missing:
            fh.write(f"{key}=\n")
    return missing


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="env-doctor",
        description="Audit a .env file against its .env.example.")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_audit = sub.add_parser("audit", help="compare .env to .env.example")
    p_audit.add_argument("--env", default=".env")
    p_audit.add_argument("--example", default=".env.example")
    p_audit.add_argument("--json", action="store_true",
                         help="print the report as JSON")
    p_audit.add_argument("--strict", action="store_true",
                         help="treat extra keys as a failure too")

    p_init = sub.add_parser("init", help="generate .env.example from .env")
    p_init.add_argument("--env", default=".env")
    p_init.add_argument("--example", default=".env.example")

    p_fix = sub.add_parser("fix", help="append missing keys to .env")
    p_fix.add_argument("--env", default=".env")
    p_fix.add_argument("--example", default=".env.example")

    args = parser.parse_args(argv)

    try:
        if args.command == "audit":
            report = audit(args.env, args.example)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print(format_report(report))
            return 1 if audit_problems(report, strict=args.strict) else 0
        if args.command == "init":
            keys = init_example(args.env, args.example)
            print(f"Wrote {args.example} with {len(keys)} keys "
                  f"(values redacted).")
            return 0
        if args.command == "fix":
            added = fix_env(args.env, args.example)
            if added:
                print(f"Added {len(added)} missing key(s) to {args.env}: "
                      + ", ".join(added))
            else:
                print(f"No missing keys; {args.env} is up to date.")
            return 0
    except (FileNotFoundError, FileExistsError) as exc:
        print(f"env-doctor: error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
