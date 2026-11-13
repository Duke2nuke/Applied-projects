#!/usr/bin/env python3
"""Secret Scrubber — redact secrets from text and log files before sharing.

A stdlib-only CLI. It scans text for well-known secret formats
(AWS keys, GitHub/Slack tokens, JWTs, private-key blocks, bearer
tokens, passwords in URLs, generic ``key = value`` assignments)
and replaces each match with a labelled placeholder such as
``[REDACTED:AWS_ACCESS_KEY]``. A JSON report counts redactions by
type without ever including a secret value.

Typical use: you are about to paste a log into a GitHub issue, a
support ticket, or a chat message, and you want to be sure no
credential goes with it.

    python3 secret_scrubber.py app.log
    cat app.log | python3 secret_scrubber.py > app.log.clean
    python3 secret_scrubber.py --in-place app.log        # keeps app.log.bak
    python3 secret_scrubber.py --check app.log           # exit 1 if secrets found
    python3 secret_scrubber.py --report report.json app.log

See README.md for the full usage, the pattern list, and the limits.
This tool reduces risk; it does not guarantee a file is secret-free.
Rotate any credential that was ever pasted anywhere unredacted.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field

PLACEHOLDER = "[REDACTED:{name}]"

# Values that look like secrets but are placeholders, examples, or
# references — never redact these, or every tutorial would be "dirty".
PLACEHOLDER_VALUES = {
    "xxx", "xxxx", "xxxxx", "your-key-here", "your_api_key_here",
    "your-api-key", "changeme", "change-me", "replace-me", "todo",
    "example", "test", "null", "none", "undefined",
}


def _is_placeholder(value):
    v = value.strip().strip("\"'").lower()
    if not v:
        return True
    if v in PLACEHOLDER_VALUES:
        return True
    if v.startswith("${") and v.endswith("}"):
        return True
    if v.startswith("<") and v.endswith(">"):
        return True
    if set(v) <= set("*x-"):
        return True
    return False


@dataclass
class Pattern:
    name: str
    regex: str
    # "whole": redact the entire match; "group": redact only group 2,
    # keeping the surrounding context (e.g. the key name or "Bearer ").
    mode: str = "whole"
    # Extra check on the matched value before redacting (e.g. Luhn).
    validator: str = ""


# Order matters: specific formats first, generic assignments last, so a
# specific token is labelled by its real type instead of "API_KEY".
PATTERNS = [
    Pattern("PRIVATE_KEY_BLOCK",
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
            r".*?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
            validator="dotall"),
    Pattern("AWS_ACCESS_KEY", r"\bAKIA[0-9A-Z]{16}\b"),
    Pattern("GITHUB_TOKEN",
            r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b"
            r"|\bgithub_pat_[A-Za-z0-9_]{22,}\b"),
    Pattern("SLACK_TOKEN", r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    Pattern("JWT",
            r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    Pattern("BEARER_TOKEN",
            r"(Bearer\s+)([A-Za-z0-9\-._~+/=]{20,})",
            mode="group"),
    Pattern("URL_PASSWORD",
            r"(://[^:/\s]+:)([^@\s/]+)(@)",
            mode="group"),
    Pattern("AWS_SECRET_KEY",
            r"(aws_secret_access_key\s*=\s*[\"']?)([A-Za-z0-9/+=]{40})([\"']?)",
            mode="group"),
    Pattern("GENERIC_SECRET",
            r"(?i)\b((?:api[_-]?key|apikey|access[_-]?token|client[_-]?secret"
            r"|secret[_-]?key|password|passwd|pwd|auth[_-]?token)"
            r"\s*[:=]\s*[\"']?)([^\s\"',;]{8,})",
            mode="group"),
]

# Opt-in patterns: off by default because they match non-secret data
# (emails in a log are often fine; card-shaped numbers often are not cards).
OPTIONAL_PATTERNS = [
    Pattern("EMAIL",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    Pattern("CREDIT_CARD",
            r"\b(?:\d[ -]?){13,19}\b",
            validator="luhn"),
]


def _luhn_ok(digits):
    digits = re.sub(r"\D", "", digits)
    if not (13 <= len(digits) <= 19):
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


@dataclass
class ScrubResult:
    text: str
    counts: dict = field(default_factory=dict)
    lines_scanned: int = 0
    lines_changed: int = 0

    @property
    def total(self):
        return sum(self.counts.values())


def _compile(pattern):
    flags = re.IGNORECASE if pattern.name == "GENERIC_SECRET" else 0
    if pattern.validator == "dotall":
        flags |= re.DOTALL
    return re.compile(pattern.regex, flags)


def _redact_value(match, pattern, counts):
    """Replacement function for one pattern; returns the redacted text."""
    # Idempotency: never redact our own placeholders, so scrubbing an
    # already-scrubbed file is a no-op instead of mangling "[REDACTED:...]".
    if "[REDACTED:" in match.group(0):
        return match.group(0)
    value = match.group(2) if pattern.mode == "group" else match.group(0)
    if pattern.validator == "luhn" and not _luhn_ok(value):
        return match.group(0)
    if pattern.mode == "group" and _is_placeholder(value):
        return match.group(0)
    counts[pattern.name] = counts.get(pattern.name, 0) + 1
    token = PLACEHOLDER.format(name=pattern.name)
    if pattern.mode == "group":
        return match.group(1) + token + (match.group(3) if match.lastindex and match.lastindex >= 3 else "")
    return token


def scrub_text(text, include_email=False, include_cards=False,
               extra_patterns=None):
    """Redact secrets in `text`; returns a ScrubResult."""
    patterns = list(PATTERNS)
    if include_email:
        patterns.append(OPTIONAL_PATTERNS[0])
    if include_cards:
        patterns.append(OPTIONAL_PATTERNS[1])
    for name, regex in (extra_patterns or []):
        patterns.append(Pattern(name, regex))

    counts = {}
    out = text
    for pattern in patterns:
        compiled = _compile(pattern)
        out = compiled.sub(lambda m: _redact_value(m, pattern, counts), out)
    lines = text.splitlines()
    changed = sum(
        1 for a, b in zip(lines, out.splitlines()) if a != b)
    # A redaction that joins/splits lines (private-key block) still counts.
    if out.count("\n") != text.count("\n"):
        changed = max(changed, 1) if counts else changed
    return ScrubResult(text=out, counts=counts,
                       lines_scanned=len(lines), lines_changed=changed)


def load_config(path):
    """Load custom patterns from JSON: {"patterns": [{"name": ..., "regex": ...}]}."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    extra = []
    for item in data.get("patterns", []):
        name = item["name"]
        regex = item["regex"]
        re.compile(regex)  # fail fast on a bad regex
        extra.append((name, regex))
    return extra


def build_report(results, counts):
    return {
        "files": results,
        "total_redactions": sum(counts.values()),
        "by_type": dict(sorted(counts.items())),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Redact secrets from text/log files before sharing.")
    parser.add_argument("files", nargs="*", metavar="FILE",
                        help="file(s) to scrub; omit to read stdin")
    parser.add_argument("-o", "--output", metavar="FILE",
                        help="write scrubbed output here (single input only)")
    parser.add_argument("--in-place", action="store_true",
                        help="rewrite each input file, keeping a .bak backup")
    parser.add_argument("--check", action="store_true",
                        help="do not modify anything; exit 1 if any secret found")
    parser.add_argument("--report", metavar="FILE",
                        help="write a JSON summary (counts only, no secret values)")
    parser.add_argument("--include-email", action="store_true",
                        help="also redact email addresses")
    parser.add_argument("--include-cards", action="store_true",
                        help="also redact Luhn-valid card-like numbers")
    parser.add_argument("--config", metavar="FILE",
                        help="JSON file with extra custom patterns")
    parser.add_argument("--list-patterns", action="store_true",
                        help="print the built-in pattern names and exit")
    args = parser.parse_args(argv)

    if args.list_patterns:
        for p in PATTERNS:
            print(p.name)
        print("EMAIL (opt-in: --include-email)")
        print("CREDIT_CARD (opt-in: --include-cards)")
        return 0

    if args.output and (len(args.files) != 1 or args.in_place):
        parser.error("--output needs exactly one input file and no --in-place")
    if args.in_place and not args.files:
        parser.error("--in-place needs at least one input file")

    extra = load_config(args.config) if args.config else []

    sources = []
    if not args.files:
        sources.append(("<stdin>", sys.stdin.read()))
    else:
        for path in args.files:
            try:
                with open(path, "r", encoding="utf-8", errors="strict") as fh:
                    sources.append((path, fh.read()))
            except (OSError, UnicodeDecodeError) as exc:
                print(f"secret_scrubber: cannot read {path}: {exc}",
                      file=sys.stderr)
                return 2

    total_counts = {}
    per_file = []
    any_secrets = False
    for name, text in sources:
        result = scrub_text(text, args.include_email, args.include_cards, extra)
        for key, value in result.counts.items():
            total_counts[key] = total_counts.get(key, 0) + value
        any_secrets = any_secrets or result.total > 0
        per_file.append({
            "file": name,
            "lines_scanned": result.lines_scanned,
            "lines_changed": result.lines_changed,
            "redactions": result.total,
            "by_type": result.counts,
        })

        if args.check:
            continue
        if args.in_place:
            with open(name + ".bak", "w", encoding="utf-8") as fh:
                fh.write(text)
            with open(name, "w", encoding="utf-8") as fh:
                fh.write(result.text)
        elif args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(result.text)
        else:
            sys.stdout.write(result.text)
            if not result.text.endswith("\n") and result.text:
                sys.stdout.write("\n")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(build_report(per_file, total_counts), fh, indent=2)
            fh.write("\n")

    if args.check:
        if any_secrets:
            for entry in per_file:
                if entry["redactions"]:
                    types = ", ".join(
                        f"{k} x{v}" for k, v in entry["by_type"].items())
                    print(f"{entry['file']}: {entry['redactions']} secret(s) "
                          f"({types})", file=sys.stderr)
            return 1
        return 0

    if args.files and not args.output and not args.in_place and len(args.files) > 1:
        pass  # multi-file stdout: outputs concatenated in order, as given
    return 0


if __name__ == "__main__":
    sys.exit(main())
