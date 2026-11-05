# Day 09 — Duplicate File Finder (Day C: community / open-source)

A small command-line tool that finds files with identical *content*
under a directory — not just identical names — and reports how much
disk space the extra copies waste. Python standard library only, no
dependencies, no installation beyond Python itself.

## Who would use this, and why

Anyone whose disk, project folder, photo library, or downloads folder
has quietly filled up with copies: a file saved twice, a folder
backed up into itself, a dataset downloaded in two places, an asset
vendored in three repos. Existing duplicate finders are often GUI
apps, paid, or OS-specific; this one is a single readable script you
can run anywhere Python runs, pipe into other tools via `--json`,
and audit in a few minutes. It is deliberately **report-only**: it
never deletes anything, because two identical files are often there
on purpose (a backup, a shared asset), and deleting the wrong copy
is the one mistake this kind of tool must not make.

Open-source framing: MIT licensed (see `LICENSE`), contributions
welcome — good first issues would be a `--delete` mode behind an
explicit confirmation prompt, a progress bar for very large trees,
and a `--format csv` output. Issues and pull requests that keep the
tool stdlib-only and report-safe are in scope.

## How to run

No dependencies — Python 3.10+ standard library only.

```bash
python3 duplicate_finder.py example            # scan a folder
python3 duplicate_finder.py ~/Downloads --json # machine-readable output
python3 duplicate_finder.py . --exclude "*.tmp" --min-size 1024
python3 test_duplicate_finder.py               # automated checks
```

Exit code is 0 when no duplicates are found and 1 when duplicates
are found (like a linter), so it can gate a script or a cleanup
check. A bad path exits 2.

Options: `--min-size BYTES` (ignore smaller files), `--exclude
PATTERN` (repeatable, fnmatch against name or relative path),
`--include-empty` (zero-byte files are skipped by default),
`--follow-symlinks` (off by default, so a symlinked folder cannot
loop the walk), `--json`.

## Example input / output (actually run, 4 Nov 2026)

Input — `example/` contains four files:

- `notes.txt` and `backup/notes-copy.txt`: byte-identical
- `notes-different.txt`: almost the same text, one character changed
- `unique.txt`: unrelated

Output:

```
Scanned 4 files: 1 duplicate group(s), 1 extra copy, 55 B recoverable.

Group 1: 2 copies, 55 B each, 55 B recoverable, sha256 68fa0d905b21...
  example/backup/notes-copy.txt
  example/notes.txt
```

The near-identical file is correctly *not* flagged: same-ish size
does not mean same content. With `--json` the same run reports
`{"files_scanned": 4, "duplicate_groups": 1, "duplicate_files": 1,
"wasted_bytes": 55}` plus the group, its size, full SHA-256, and
sorted file list.

## How it works

Two phases, so large trees stay fast:

1. **Group by size.** Files of different sizes cannot be duplicates,
   so only files that share a size with at least one other file are
   ever hashed. In a tree of mostly unique sizes, almost nothing
   gets hashed at all.
2. **Hash and group by content.** Each candidate is read in 64 KiB
   chunks and SHA-256 hashed; files are grouped by (size, hash).
   Only byte-identical files are reported.

Unreadable or vanished files are skipped rather than crashing the
scan, and symlinks are skipped by default.

## 2-minute interview explainer

**Problem:** duplicate files waste disk and confuse projects, but
finding them by name misses renamed copies, and comparing every
file against every other file is O(n²) and slow.

**Approach:** a two-phase filter — size first, SHA-256 second.
Size grouping is cheap and eliminates almost everything; hashing
only the survivors makes the scan near-linear in practice while
staying exact (same size plus same SHA-256 means same bytes, for
all practical purposes). The tool is report-only by design, with
JSON output for scripting and flags for minimum size, excludes,
and empty files.

**Results:** on the bundled example, 4 files scanned, 1 duplicate
group found, 55 B recoverable — and the deliberately near-identical
file correctly excluded. 6 automated tests pass, covering grouping
across folders, same-size-different-content, minimum size,
excludes, empty files, and wasted-bytes arithmetic.

**Limits:** it compares exact bytes, so it will not catch
near-duplicates (a resized image, a re-encoded video, a file with
one edited line) — that needs perceptual or fuzzy hashing, which is
a different tool. SHA-256 collisions are theoretically possible but
not a practical concern here. Very large trees are scanned
single-threaded; parallel hashing would be the next optimisation.
It also trusts file size + hash rather than reading both files
byte-for-byte after hashing, which is the standard trade-off every
duplicate finder makes.
