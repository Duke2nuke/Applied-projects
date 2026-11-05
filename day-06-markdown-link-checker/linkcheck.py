#!/usr/bin/env python3
"""linkcheck — find broken links in Markdown files.

Scans Markdown files for links and reports which ones are broken:

* local file links  — the target file must exist, relative to the
  Markdown file that links to it
* anchors           — ``#heading`` must match a heading in the target
  file (GitHub-style slug: lowercase, spaces to hyphens, punctuation
  stripped)
* remote links      — only checked with ``--remote`` (a network request);
  otherwise reported as UNCHECKED so a run never needs the network
* ``mailto:`` links — reported as SKIPPED, not broken

Links inside fenced code blocks and inline code are ignored, because
they are examples, not real links.

Standard library only. Exit code 1 if any broken link is found, else 0.

Usage:
    python linkcheck.py docs/
    python linkcheck.py README.md docs/ --remote
    python linkcheck.py docs/ --format json
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

INLINE_LINK_RE = re.compile(
    r"!?\[[^\]]*\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)"
)
REFERENCE_DEF_RE = re.compile(r"^\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
AUTOLINK_RE = re.compile(r"<(https?://[^>]+)>")
FENCED_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]+`")


def slugify(heading: str) -> str:
    """GitHub-style heading anchor: lowercase, spaces -> hyphens."""
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    return re.sub(r"\s+", "-", slug)


def headings_of(text: str) -> set:
    """Anchor slugs of all ATX headings in a Markdown document."""
    return {
        slugify(heading)
        for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", text, re.MULTILINE)
    }


def strip_code(text: str) -> str:
    return INLINE_CODE_RE.sub("", FENCED_BLOCK_RE.sub("", text))


def extract_links(text: str) -> list:
    """All link targets in a document, in order, deduplicated."""
    clean = strip_code(text)
    found = []
    for pattern in (INLINE_LINK_RE, REFERENCE_DEF_RE, AUTOLINK_RE):
        for match in pattern.finditer(clean):
            target = match.group(1)
            if target not in found:
                found.append(target)
    return found


def check_remote(url: str, timeout: int = 10) -> tuple:
    """Return (ok, detail) for an http(s) URL, HEAD with GET fallback."""
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status < 400, f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        if exc.code == 405:  # HEAD not allowed; try GET
            try:
                with urllib.request.urlopen(url, timeout=timeout) as response:
                    return response.status < 400, f"HTTP {response.status}"
            except Exception as get_exc:  # noqa: BLE001 - report, don't crash
                return False, f"{type(get_exc).__name__}: {get_exc}"
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        return False, f"{type(exc).__name__}: {exc}"


def check_link(source: Path, target: str, root: Path, remote: bool) -> dict:
    """Check one link target. Returns a result dict with a status."""
    result = {"source": str(source), "target": target}
    if target.startswith("mailto:") or target.startswith("tel:"):
        return {**result, "status": "SKIPPED", "detail": "contact link, not checked"}
    if target.startswith(("http://", "https://")):
        if not remote:
            return {**result, "status": "UNCHECKED", "detail": "remote, use --remote"}
        ok, detail = check_remote(target)
        return {**result, "status": "OK" if ok else "BROKEN", "detail": detail}

    path_part, _, anchor = target.partition("#")
    if not path_part:  # anchor-only link: same file
        target_file = source
    elif path_part.startswith("/"):  # root-relative
        target_file = root / path_part.lstrip("/")
    else:  # relative to the linking file
        target_file = (source.parent / path_part).resolve()
    if not target_file.exists():
        return {**result, "status": "BROKEN", "detail": "file does not exist"}
    if anchor and target_file.suffix.lower() == ".md":
        anchors = headings_of(target_file.read_text(encoding="utf-8", errors="replace"))
        if anchor.lower() not in anchors:
            return {**result, "status": "BROKEN", "detail": "anchor not found in file"}
    return {**result, "status": "OK", "detail": "exists"}


def collect_markdown(paths: list) -> list:
    """Expand files/dirs on the command line into sorted .md files."""
    files = []
    for raw in paths:
        path = Path(raw)
        if path.is_file() and path.suffix.lower() == ".md":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
    return files


def run(paths: list, remote: bool = False) -> dict:
    """Check every link in every Markdown file under paths."""
    results = []
    for md_file in collect_markdown(paths):
        text = md_file.read_text(encoding="utf-8", errors="replace")
        root = Path(paths[0]) if len(paths) == 1 else md_file.parent
        # Root for "/..." links: the first path if it is a directory,
        # otherwise the linking file's own directory.
        root = Path(paths[0]) if Path(paths[0]).is_dir() else md_file.parent
        for target in extract_links(text):
            results.append(check_link(md_file, target, root, remote))
    broken = [r for r in results if r["status"] == "BROKEN"]
    return {"results": results, "broken": broken,
            "total": len(results), "broken_count": len(broken)}


def report_text(report: dict) -> str:
    lines = []
    for result in report["results"]:
        lines.append(
            f'{result["status"]:9} {result["source"]} -> '
            f'{result["target"]} ({result["detail"]})'
        )
    lines.append(
        f'\n{report["total"]} links checked, '
        f'{report["broken_count"]} broken.'
    )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Find broken links in Markdown.")
    parser.add_argument("paths", nargs="+", help="Markdown files or directories")
    parser.add_argument("--remote", action="store_true",
                        help="also check http(s) links over the network")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    report = run(args.paths, remote=args.remote)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(report_text(report))
    return 1 if report["broken_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
