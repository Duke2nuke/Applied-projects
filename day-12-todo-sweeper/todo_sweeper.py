#!/usr/bin/env python3
"""todo-sweeper: find the TODOs, FIXMEs and HACKs hiding in a codebase.

Every project accumulates marker comments — TODO, FIXME, HACK, XXX,
NOTE, BUG — and they quietly go stale: the person who wrote them left,
the bug got fixed another way, or the "temporary" hack is now load-
bearing. This tool sweeps a directory tree, collects every marker with
its file, line number and text, and prints a grouped report (or JSON
for scripting). It never edits anything: report-only, like a linter.

Standard library only. Python 3.10+.

Usage:
    python3 todo_sweeper.py [PATH] [--tag TODO,FIXME] [--json]
                            [--report out.md] [--exclude PATTERN]
                            [--extensions .py,.js] [--no-hidden]

Exit codes: 0 = no markers found, 1 = markers found, 2 = bad usage/path.
"""

import argparse
import fnmatch
import json
import os
import re
import sys

TAGS = ("TODO", "FIXME", "HACK", "XXX", "NOTE", "BUG")

# A marker is a tag word at the start of a comment (or of the line),
# optionally followed by "(name)" and/or ":", then the note text.
# Case-insensitive. The tag must be the first word after a comment
# opener, so "TODOLIST", "fixes the bug" and "'TODO'" in a string
# literal are not markers.
TAG_RE = re.compile(
    r"(?P<tag>TODO|FIXME|HACK|XXX|NOTE|BUG)\b"
    r"(?:\s*\((?P<owner>[^)]{1,40})\))?"
    r"\s*:?\s*(?P<text>.*)$",
    re.IGNORECASE,
)
LEADING_COMMENT_RE = re.compile(r"^\s*(?:#|//|/\*|\*|<!--|--|;|%|-)\s*")
OPENERS = ("<!--", "//", "/*", "#", "--", "*", ";", "%", "-")

# Directories never worth sweeping: version control, dependencies,
# caches, build output, virtualenvs.
SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv",
    "venv", ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    "target", ".idea", ".vscode",
}
MAX_FILE_BYTES = 2 * 1024 * 1024  # skip files larger than 2 MiB


def is_binary(path, chunk_size=8192):
    """Heuristic: a NUL byte in the first chunk means binary."""
    try:
        with open(path, "rb") as fh:
            return b"\x00" in fh.read(chunk_size)
    except OSError:
        return True


def clean_text(raw):
    """Strip leading comment markers and trailing comment closers."""
    text = LEADING_COMMENT_RE.sub("", raw).strip()
    text = re.sub(r"\s*(?:\*/|-->)\s*$", "", text).strip()
    return text


def scan_file(path, rel_path, tags):
    """Return a list of marker dicts found in one text file.

    A marker counts only when its tag is the first word of a comment:
    the start of the line, or right after a comment opener (#, //,
    /*, <!--, ...), so prose that merely contains the word "bug" or a
    string literal 'TODO' is not flagged.
    """
    found = []
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as fh:
            lines = fh.readlines()
    except (OSError, UnicodeDecodeError):
        return found
    for lineno, line in enumerate(lines, start=1):
        raw = line.rstrip("\n")
        tails = [raw]
        for opener in OPENERS:
            start = 0
            while True:
                idx = raw.find(opener, start)
                if idx == -1:
                    break
                tails.append(raw[idx + len(opener):])
                start = idx + len(opener)
        for tail in tails:
            stripped = LEADING_COMMENT_RE.sub("", tail.strip())
            match = TAG_RE.match(stripped)
            if not match:
                continue
            tag = match.group("tag").upper()
            if tag not in tags:
                continue
            found.append({
                "file": rel_path,
                "line": lineno,
                "tag": tag,
                "owner": match.group("owner"),
                "text": clean_text(match.group(0)),
            })
            break
    return found


def excluded(rel_path, name, patterns):
    return any(
        fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_path, pat)
        for pat in patterns
    )


def sweep(root, tags, exclude, extensions, skip_hidden):
    """Walk root and return (markers, files_scanned, files_skipped)."""
    markers = []
    scanned = 0
    skipped = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        rel_dir = os.path.relpath(dirpath, root)
        # Prune skipped / hidden directories in place so walk never enters.
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS
            and not (skip_hidden and d.startswith("."))
            and not excluded(os.path.join(rel_dir, d) if rel_dir != "." else d,
                             d, exclude)
        ]
        for name in sorted(filenames):
            rel_path = os.path.join(rel_dir, name) if rel_dir != "." else name
            if skip_hidden and name.startswith("."):
                skipped += 1
                continue
            if excluded(rel_path, name, exclude):
                skipped += 1
                continue
            if extensions and not any(name.endswith(ext) for ext in extensions):
                skipped += 1
                continue
            full = os.path.join(dirpath, name)
            if os.path.islink(full) or not os.path.isfile(full):
                skipped += 1
                continue
            if os.path.getsize(full) > MAX_FILE_BYTES or is_binary(full):
                skipped += 1
                continue
            scanned += 1
            markers.extend(scan_file(full, rel_path, tags))
    markers.sort(key=lambda m: (m["tag"], m["file"], m["line"]))
    return markers, scanned, skipped


def text_report(root, markers, scanned, skipped):
    lines = []
    by_tag = {}
    for m in markers:
        by_tag.setdefault(m["tag"], []).append(m)
    total = len(markers)
    lines.append(
        f"Scanned {scanned} file(s) under {root}: "
        f"{total} marker(s) found"
        + (f" ({', '.join(f'{t}: {len(v)}' for t, v in sorted(by_tag.items()))})"
           if total else "")
        + "."
    )
    if skipped:
        lines.append(f"Skipped {skipped} file(s) (binary, oversized, hidden or excluded).")
    if not total:
        lines.append("Clean — no TODO, FIXME, HACK, XXX, NOTE or BUG markers.")
        return "\n".join(lines) + "\n"
    for tag in sorted(by_tag):
        lines.append(f"\n## {tag} ({len(by_tag[tag])})")
        for m in by_tag[tag]:
            owner = f" ({m['owner']})" if m["owner"] else ""
            lines.append(f"  {m['file']}:{m['line']}{owner} {m['text']}")
    return "\n".join(lines) + "\n"


def markdown_report(root, markers, scanned, skipped):
    lines = [f"# TODO sweep: `{root}`", "",
             f"Scanned **{scanned}** file(s), **{len(markers)}** marker(s) found."]
    if skipped:
        lines.append(f"Skipped {skipped} file(s) (binary, oversized, hidden or excluded).")
    by_tag = {}
    for m in markers:
        by_tag.setdefault(m["tag"], []).append(m)
    for tag in sorted(by_tag):
        lines.append(f"\n## {tag} ({len(by_tag[tag])})")
        for m in by_tag[tag]:
            owner = f" (@{m['owner']})" if m["owner"] else ""
            lines.append(f"- `{m['file']}:{m['line']}`{owner} {m['text']}")
    if not markers:
        lines.append("\nClean — no markers found.")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Sweep a directory tree for TODO/FIXME/HACK/XXX/NOTE/BUG markers.")
    parser.add_argument("path", nargs="?", default=".",
                        help="directory to sweep (default: current directory)")
    parser.add_argument("--tag", default=",".join(TAGS),
                        help="comma-separated tags to look for "
                             f"(default: {','.join(TAGS)})")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable JSON output")
    parser.add_argument("--report", metavar="FILE",
                        help="also write a Markdown report to FILE")
    parser.add_argument("--exclude", action="append", default=[],
                        metavar="PATTERN",
                        help="fnmatch pattern to skip (repeatable, "
                             "matched against file name or relative path)")
    parser.add_argument("--extensions", default="",
                        help="comma-separated file extensions to include, "
                             "e.g. .py,.js (default: all text files)")
    parser.add_argument("--no-hidden", action="store_true",
                        help="skip hidden files and directories")
    args = parser.parse_args(argv)

    tags = {t.strip().upper() for t in args.tag.split(",") if t.strip()}
    unknown = tags - set(TAGS)
    if unknown:
        print(f"error: unknown tag(s): {', '.join(sorted(unknown))} "
              f"(known: {', '.join(TAGS)})", file=sys.stderr)
        return 2
    if not os.path.isdir(args.path):
        print(f"error: not a directory: {args.path}", file=sys.stderr)
        return 2
    extensions = tuple(e.strip() for e in args.extensions.split(",") if e.strip())

    markers, scanned, skipped = sweep(
        args.path, tags, args.exclude, extensions, args.no_hidden)

    if args.report:
        try:
            with open(args.report, "w", encoding="utf-8") as fh:
                fh.write(markdown_report(args.path, markers, scanned, skipped))
        except OSError as exc:
            print(f"error: cannot write report: {exc}", file=sys.stderr)
            return 2

    if args.json:
        print(json.dumps({
            "path": args.path,
            "files_scanned": scanned,
            "files_skipped": skipped,
            "markers_found": len(markers),
            "by_tag": {t: sum(1 for m in markers if m["tag"] == t)
                       for t in sorted({m["tag"] for m in markers})},
            "markers": markers,
        }, indent=2))
    else:
        print(text_report(args.path, markers, scanned, skipped), end="")

    return 1 if markers else 0


if __name__ == "__main__":
    raise SystemExit(main())
