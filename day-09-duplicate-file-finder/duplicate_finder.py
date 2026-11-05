#!/usr/bin/env python3
"""Find duplicate files under a directory, by content, not by name.

Two-phase approach, so large trees stay fast:
  1. Group files by size — files of different sizes cannot be duplicates,
     so only same-size files ever get hashed.
  2. Hash each same-size candidate (SHA-256, read in chunks) and group
     by (size, hash). Only files with identical bytes are reported.

Safety: this tool only *reports*. It never deletes, moves, or modifies
anything. Deciding which copy to keep is left to the user, because two
identical files in different folders are often there on purpose
(a backup, a vendored copy, a shared asset).

Usage:
    python3 duplicate_finder.py [path] [--min-size BYTES]
                                [--exclude PATTERN ...] [--include-empty]
                                [--follow-symlinks] [--json]
"""

import argparse
import fnmatch
import hashlib
import json
import os
import sys

CHUNK_SIZE = 64 * 1024  # 64 KiB


def iter_files(root, exclude=(), follow_symlinks=False):
    """Yield file paths under root, honouring exclude patterns.

    An exclude pattern is matched with fnmatch against the file name
    and against its path relative to root, so both ``*.tmp`` and
    ``build/*`` style patterns work. Symlinks are skipped unless
    follow_symlinks is set, so a symlinked folder cannot loop the walk.
    """
    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        if not follow_symlinks:
            dirnames[:] = [d for d in dirnames
                           if not os.path.islink(os.path.join(dirpath, d))]
        for name in filenames:
            path = os.path.join(dirpath, name)
            if not follow_symlinks and os.path.islink(path):
                continue
            rel = os.path.relpath(path, root)
            if any(fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel, pat)
                   for pat in exclude):
                continue
            yield path


def hash_file(path):
    """SHA-256 of a file, read in chunks so big files stay memory-light."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicates(root, min_size=1, exclude=(), include_empty=False,
                    follow_symlinks=False):
    """Return (groups, summary) for duplicates under root.

    A group is {"size": int, "hash": str, "files": [sorted paths]}.
    Groups are sorted by wasted bytes (descending), then by size.
    Wasted bytes = bytes that would be freed by keeping one copy of
    each group and deleting the rest: (n_copies - 1) * size.
    """
    if not os.path.isdir(root):
        raise ValueError(f"not a directory: {root}")

    if include_empty:
        effective_min = 0
    else:
        effective_min = max(min_size, 1)  # zero-byte files skipped by default

    # Phase 1: group by size.
    by_size = {}
    for path in iter_files(root, exclude, follow_symlinks):
        try:
            size = os.path.getsize(path)
        except OSError:
            continue  # unreadable / vanished mid-walk: skip, don't crash
        if size < effective_min:
            continue
        by_size.setdefault(size, []).append(path)

    # Phase 2: hash only files that share a size with at least one other.
    by_content = {}
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        for path in paths:
            try:
                digest = hash_file(path)
            except OSError:
                continue
            by_content.setdefault((size, digest), []).append(path)

    groups = [{"size": size, "hash": digest, "files": sorted(paths)}
              for (size, digest), paths in by_content.items() if len(paths) > 1]
    groups.sort(key=lambda g: (-(len(g["files"]) - 1) * g["size"], -g["size"]))

    total_files = sum(len(paths) for paths in by_size.values())
    duplicate_files = sum(len(g["files"]) - 1 for g in groups)
    wasted = sum((len(g["files"]) - 1) * g["size"] for g in groups)
    summary = {
        "files_scanned": total_files,
        "duplicate_groups": len(groups),
        "duplicate_files": duplicate_files,
        "wasted_bytes": wasted,
    }
    return groups, summary


def format_bytes(n):
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unit == "GiB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GiB"


def report_text(groups, summary):
    extra = summary['duplicate_files']
    lines = [
        f"Scanned {summary['files_scanned']} files: "
        f"{summary['duplicate_groups']} duplicate group(s), "
        f"{extra} extra {'copy' if extra == 1 else 'copies'}, "
        f"{format_bytes(summary['wasted_bytes'])} recoverable.",
    ]
    for i, group in enumerate(groups, 1):
        wasted = (len(group["files"]) - 1) * group["size"]
        lines.append(
            f"\nGroup {i}: {len(group['files'])} copies, "
            f"{format_bytes(group['size'])} each, "
            f"{format_bytes(wasted)} recoverable, sha256 {group['hash'][:12]}..."
        )
        for path in group["files"]:
            lines.append(f"  {path}")
    if not groups:
        lines.append("No duplicates found.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Find duplicate files by content (size, then SHA-256).")
    parser.add_argument("path", nargs="?", default=".",
                        help="directory to scan (default: current directory)")
    parser.add_argument("--min-size", type=int, default=1,
                        help="ignore files smaller than this many bytes")
    parser.add_argument("--exclude", action="append", default=[],
                        help="fnmatch pattern to skip (repeatable)")
    parser.add_argument("--include-empty", action="store_true",
                        help="also treat zero-byte files as duplicates")
    parser.add_argument("--follow-symlinks", action="store_true",
                        help="follow symlinked files and directories")
    parser.add_argument("--json", action="store_true",
                        help="print machine-readable JSON instead of text")
    args = parser.parse_args(argv)

    try:
        groups, summary = find_duplicates(
            args.path, min_size=args.min_size, exclude=args.exclude,
            include_empty=args.include_empty,
            follow_symlinks=args.follow_symlinks)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"summary": summary, "groups": groups}, indent=2))
    else:
        print(report_text(groups, summary))
    return 0 if not groups else 1  # exit 1 when duplicates found, like a linter


if __name__ == "__main__":
    raise SystemExit(main())
