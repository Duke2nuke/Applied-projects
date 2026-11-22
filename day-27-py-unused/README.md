# py-unused — Find (and remove) unused imports in Python code

Day 27 — Community / open-source build. Standard library only, no
dependencies to install.

## What it does

`py-unused` scans a Python file or directory and reports every import
that is never used — the dead `import os` left over from a refactor,
the `from collections import OrderedDict` nobody calls any more.
It prints `file:line` findings, can emit JSON for CI, exits non-zero
when it finds anything, and `--fix` removes the unused names from
single-line import statements in place.

## Who would use this, and why

Any Python developer, on any project. Unused imports are the most
common lint finding in real codebases: they slow down imports,
confuse readers about what a module depends on, and hide real
dependencies. Full linters (ruff, flake8) already flag them, but
they need installing and configuring; `py-unused` is one file, zero
dependencies, copy it into a repo or a pre-commit hook and it just
runs. It is also a handy CI gate: fail the build if a PR adds an
unused import.

## Install / run

```bash
# No install step: standard library only (Python 3.8+).
python py_unused.py path/to/file_or_directory
python py_unused.py src/ --exclude tests --exclude venv
python py_unused.py src/ --json          # machine-readable output
python py_unused.py src/ --fix           # remove unused imports in place
python py_unused.py --help
```

Exit codes: `0` = no unused imports, `1` = unused imports found,
`2` = usage error (e.g. no Python files found).

## Example

`examples/messy.py` imports `json`, `sys`, `Counter`, `OrderedDict`,
`Path` and `requests`, but only uses `json`, `Counter` and `Path`:

```bash
$ python py_unused.py examples/messy.py
examples/messy.py:8: 'sys' is imported but never used (import sys)
examples/messy.py:9: 'OrderedDict' is imported but never used (from collections import Counter, OrderedDict)
examples/messy.py:12: 'requests' is imported but never used (import requests)
py-unused: 3 unused import(s) in 1 file(s)
$ echo $?
1
```

```bash
$ python py_unused.py examples/clean.py
py-unused: no unused imports in 1 file(s)
$ echo $?
0
```

`--fix` on a copy of `messy.py` removed exactly those 3 imports and
the file still runs (`Counter({'a': 2, 'b': 1})`).

JSON output (`--json`) for the same file:

```json
[
  {
    "file": "examples/messy.py",
    "line": 8,
    "name": "sys",
    "statement": "import sys",
    "module": "sys"
  },
  {
    "file": "examples/messy.py",
    "line": 9,
    "name": "OrderedDict",
    "statement": "from collections import Counter, OrderedDict",
    "module": "collections"
  },
  {
    "file": "examples/messy.py",
    "line": 12,
    "name": "requests",
    "statement": "import requests",
    "module": "requests"
  }
]
```

## How it works

It parses each file with Python's own `ast` module, so it understands
real code, not regexes:

- Collects every bound import name (`import x`, `import x as y`,
  `from m import a, b as c`), including relative imports.
- A name counts as used if it appears as a `Name` node, as the root
  of an attribute access (`os.path.join` uses `os`), in a string
  annotation (`def f(x: "User")`), or in `__all__`.
- Skips what it cannot judge: `from x import *` (unknown names),
  `from __future__ import ...` (a directive), imports inside
  `if TYPE_CHECKING:` blocks, and `__init__.py` files by default
  (their imports are usually re-exports; use `--include-init` to
  scan them).
- `--fix` only rewrites single-line import statements. Multi-line
  (parenthesised) imports are reported but left untouched, so a fix
  never rewrites a statement it cannot parse safely.

## Tests

```bash
python -m unittest test_py_unused -v
```

27/27 tests pass, covering detection (plain/aliased/from/star/future/
`TYPE_CHECKING`/`__all__`/string annotations/docstrings), file
discovery (excludes, `__init__.py` handling), `--fix` (single name,
whole line, alias kept, multi-line skipped) and CLI exit codes.
The tool was also run on its own source: no unused imports in
`py_unused.py` or `test_py_unused.py`.

## Limits (honest)

- Static analysis only: names used dynamically (`getattr`, `eval`,
  `importlib`, plugin-style string lookups) are reported as unused.
  If your code loads modules by string name, check the report before
  running `--fix`.
- A name mentioned in a docstring or a plain string literal is not
  counted as used — only strings in annotation position or `__all__`
  count. This is deliberate: otherwise a docstring naming an import
  would hide a real unused import.
- `--fix` does not collapse the blank line left behind when a whole
  import line is removed; run a formatter afterwards if that matters.
- Syntax errors: the file is skipped with a warning on stderr and
  the rest of the scan still runs.

## Licence and contributing

MIT licensed — see `LICENSE`. Contributions welcome: open an issue or
a pull request. Good first contributions: respect `# noqa: F401`
comments, support `__init__.py` re-export detection via `__all__`,
or add a `--check` mode that prints a diff instead of editing.

## 2-minute explainer

**Problem:** dead imports pile up in every Python project — a leftover
`import requests` after a refactor, an `OrderedDict` nobody calls.
They mislead readers, slow imports, and full linters need setup.

**Approach:** one stdlib-only script built on Python's `ast` module.
It parses each file, collects the names each import binds, then
checks whether each name is actually referenced — as a variable, an
attribute root, a string annotation, or an `__all__` entry. Imports
it cannot judge (star imports, `TYPE_CHECKING` blocks, `__init__.py`
re-exports) are skipped rather than falsely flagged. Findings print
as `file:line`, with JSON and exit codes for CI, and `--fix` removes
unused names from single-line import statements.

**Results:** on the bundled `examples/messy.py` it finds exactly the
3 genuinely unused imports (`sys`, `OrderedDict`, `requests`) out of
6, misses none of the 3 used ones, and `--fix` removes the 3 while
the file still runs. 27/27 unit tests pass, and the tool is clean on
its own source.

**Limits:** it cannot see dynamic uses (`getattr`, `eval`), so check
before `--fix` on plugin-style code; multi-line imports are reported
but not auto-fixed.
