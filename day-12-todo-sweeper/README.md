# Day 12 — TODO Sweeper (Day C: community / open-source)

A small command-line tool that sweeps a directory tree for the marker
comments every codebase accumulates — `TODO`, `FIXME`, `HACK`, `XXX`,
`NOTE`, `BUG` — and reports them grouped by tag, with file and line
number. Python standard library only, no dependencies, no
installation beyond Python itself.

## Who would use this, and why

Anyone inheriting a codebase, preparing a release, or doing a
spring-clean of a repo they have lived in for a while: marker
comments go stale silently — the person who wrote them left, the
bug got fixed another way, or the "temporary" hack is now
load-bearing and nobody remembers why. Existing answers are either
a bare `grep -r TODO`, which drowns you in false positives
("TODOLIST", "fixes the bug", a `'TODO'` string literal), or a
full-blown static-analysis setup. This is the middle ground: one
readable script, comment-aware matching (a marker only counts when
its tag is the first word of a comment), grouping by tag, JSON
output for scripting, and a Markdown report you can paste into an
issue or a PR. It is deliberately **report-only**: it never edits
anything, because deleting someone else's TODO is a decision, not
a cleanup.

Open-source framing: MIT licensed (see `LICENSE`), contributions
welcome — good first issues would be a `--since` filter using git
blame age, a `--format csv` output, and per-tag severity config.
Issues and pull requests that keep the tool stdlib-only and
report-safe are in scope.

## How to run

No dependencies — Python 3.10+ standard library only.

```bash
python3 todo_sweeper.py example              # sweep a folder
python3 todo_sweeper.py . --tag TODO,FIXME   # only some tags
python3 todo_sweeper.py ~/project --json     # machine-readable output
python3 todo_sweeper.py . --report sweep.md  # also write a Markdown report
python3 todo_sweeper.py . --exclude "*.min.js" --extensions .py,.js
python3 test_todo_sweeper.py                 # automated checks
```

Exit code is 0 when no markers are found and 1 when markers are
found (like a linter), so it can gate a script or a pre-commit
check. A bad path or unknown tag exits 2.

Options: `--tag TAG,...` (default: `TODO,FIXME,HACK,XXX,NOTE,BUG`),
`--json`, `--report FILE` (Markdown), `--exclude PATTERN`
(repeatable, fnmatch against file name or relative path),
`--extensions .py,.js` (only those files), `--no-hidden` (skip
hidden files and directories). `.git`, `node_modules`,
`__pycache__`, virtualenvs, build output, binary files and files
over 2 MiB are always skipped.

## Example input / output (actually run, 7 Nov 2026)

Input — `example/` contains two files with planted markers
(synthetic demo data):

- `app.py`: one `TODO`, one `FIXME`, one `HACK`
- `sub/notes.md`: one `NOTE`, one `XXX`

Output:

```
Scanned 2 file(s) under example: 5 marker(s) found (FIXME: 1, HACK: 1, NOTE: 1, TODO: 1, XXX: 1).

## FIXME (1)
  app.py:11 FIXME: rounding error when prices have more than 2 decimals

## HACK (1)
  app.py:16 HACK: the old API expects a trailing comma, remove after migration

## NOTE (1)
  sub/notes.md:4 NOTE: the deploy checklist lives in docs/deploy.md

## TODO (1)
  app.py:5 TODO: support pagination for large user lists

## XXX (1)
  sub/notes.md:5 XXX: the staging URL in the wiki is out of date
```

Exit code 1, as designed — markers were found. With `--json` the
same run reports `{"files_scanned": 2, "markers_found": 5, "by_tag":
{"FIXME": 1, "HACK": 1, "NOTE": 1, "TODO": 1, "XXX": 1}}` plus the
full marker list with file, line, tag, owner and text.

## How it works

1. **Walk and prune.** `os.walk` skips version-control, dependency,
   cache and build directories in place, plus binary files (NUL-byte
   check), oversized files, symlinks and user `--exclude` patterns —
   so a sweep of a big repo stays fast and never follows a symlinked
   folder into a loop.
2. **Comment-aware matching.** For each line, the tag must be the
   first word of a comment: at the start of the line, or right after
   a comment opener (`#`, `//`, `/*`, `<!--`, `--`, `;`, `%`, `-`).
   That is what keeps `TODOLIST`, "fixes the bug", and a `'TODO'`
   string literal out of the results — the failure mode of plain
   grep. An optional `(owner)` after the tag is captured separately.
3. **Group and report.** Markers are sorted by tag, file and line,
   then printed as a grouped text report, JSON, or a Markdown file
   for pasting into an issue.

## 2-minute interview explainer

**Problem:** marker comments (`TODO`, `FIXME`, `HACK`...) rot —
nobody re-reads them, so stale ones survive for years and real
ones hide in noise. Plain `grep -r TODO` is the usual answer, but
it flags `TODOLIST`, the word "bug" in a sentence, and string
literals, so teams learn to ignore its output.

**Approach:** a stdlib-only CLI that walks a tree (pruning `.git`,
`node_modules`, caches, binaries and oversized files), then applies
a comment-aware rule: a marker only counts when its tag is the
first word of a comment — line start or right after a comment
opener — with an optional `(owner)` captured separately. Results
are grouped by tag with file:line, plus JSON output for scripting
and a Markdown report for issues, and a linter-style exit code
(0 clean, 1 markers found) so it can gate a check.

**Results:** on the bundled example, 2 files scanned, 5 markers
found — exactly the planted ones, one per tag. 7 automated tests
pass, covering all six tags, owners and comment styles
(`#`, `//`, `/* */`, `<!-- -->`), false positives on similar
words and string literals, `.git`/binary/exclude skipping, the
tag filter, JSON output, and the exit codes.

**Limits:** it reads comments only, so it cannot tell a stale
marker from a live one — that still needs a human, which is why
the tool is report-only. It does not use git history, so there is
no age or author data (a `--since` filter via git blame is the
natural next feature). The 2 MiB file cap and the fixed opener
list mean exotic comment styles in unusual languages may be
missed; the opener list is one constant to extend.
