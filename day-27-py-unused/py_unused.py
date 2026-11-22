"""py-unused: find (and optionally remove) unused imports in Python code.

Standard library only. Point it at a file or a directory and it reports
every imported name that is never used, with file:line, a JSON mode for
CI, and a --fix mode that removes the unused names from single-line
import statements.

Usage:
    python py_unused.py [path ...] [--exclude PATTERN ...] [--json]
                        [--fix] [--include-init]

Exit codes: 0 = no unused imports, 1 = unused imports found,
2 = usage error (a file could not be parsed).
"""

import argparse
import ast
import json
import os
import re
import sys

VERSION = "1.0.0"

DEFAULT_EXCLUDES = {".git", "__pycache__", ".venv", "venv", "node_modules",
                    ".tox", ".eggs", "build", "dist", ".mypy_cache"}
SKIP_DIRS = DEFAULT_EXCLUDES

# Names that are imported for their side effect / re-export value and are
# never "used" in the normal sense. __future__ imports are directives.
ALWAYS_KEEP = {"annotations"}  # from __future__ import annotations


class UnusedImport:
    """One unused import: the bound name, where it was imported, and how."""

    def __init__(self, name, lineno, end_lineno, statement, module):
        self.name = name
        self.lineno = lineno
        self.end_lineno = end_lineno
        self.statement = statement  # e.g. "import os" / "from x import y"
        self.module = module        # e.g. "os" / "x" / None for plain import

    def to_dict(self, path):
        return {"file": path, "line": self.lineno, "name": self.name,
                "statement": self.statement, "module": self.module}

    def __repr__(self):  # pragma: no cover - debugging helper
        return "UnusedImport(%r, line %d)" % (self.name, self.lineno)


def _bound_name(alias):
    """The name an import binds in the importing module."""
    if alias.asname:
        return alias.asname
    return alias.name.split(".")[0]


class _ImportCollector(ast.NodeVisitor):
    """Collect imports and used names from one module AST.

    Tracks whether we are inside an `if TYPE_CHECKING:` block, because
    imports there exist for type checkers, not runtime code.
    """

    def __init__(self):
        self.imports = []       # list of dicts, one per bound name
        self.used = set()       # names referenced anywhere
        self._type_checking = 0

    def visit_If(self, node):
        test = node.test
        is_tc = (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or \
            (isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING")
        if is_tc:
            self._type_checking += 1
            self.generic_visit(node)
            self._type_checking -= 1
        else:
            self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append({
                "name": _bound_name(alias),
                "lineno": node.lineno,
                "end_lineno": node.end_lineno or node.lineno,
                "statement": "import " + ", ".join(
                    a.name + (" as " + a.asname if a.asname else "")
                    for a in node.names),
                "module": alias.name,
                "kind": "import",
                "type_checking": self._type_checking > 0,
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module == "__future__":
            # Directive, not a runtime name.
            self.generic_visit(node)
            return
        for alias in node.names:
            if alias.name == "*":
                # Star import: we cannot know which names it provides.
                continue
            self.imports.append({
                "name": _bound_name(alias),
                "lineno": node.lineno,
                "end_lineno": node.end_lineno or node.lineno,
                "statement": "from %s import %s" % (
                    "." * node.level + (node.module or ""),
                    ", ".join(a.name + (" as " + a.asname if a.asname else "")
                              for a in node.names)),
                "module": "." * node.level + (node.module or ""),
                "kind": "from",
                "type_checking": self._type_checking > 0,
            })
        self.generic_visit(node)

    def visit_Name(self, node):
        self.used.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # `os.path.join` uses `os`, the root Name; visit_Name covers it,
        # but walk the value explicitly so the root is never missed.
        self.generic_visit(node)

    def _use_words_in_strings(self, node):
        """Mark words in string constants under `node` as used.

        Only called for string constants in annotation position (or
        __all__): a docstring or a random string literal that happens
        to mention an imported name is NOT a use. Treating every
        string as a use would hide real unused imports whenever a
        docstring names them.
        """
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]*",
                                       child.value):
                    self.used.add(word)

    def _use_annotations(self, node):
        args = getattr(node, "args", None)
        if args is not None:
            slots = list(args.posonlyargs) + list(args.args) + \
                list(args.kwonlyargs)
            for arg in slots + [args.vararg, args.kwarg]:
                if arg is not None and arg.annotation is not None:
                    self._use_words_in_strings(arg.annotation)
        if getattr(node, "returns", None) is not None:
            self._use_words_in_strings(node.returns)

    def visit_FunctionDef(self, node):
        self._use_annotations(node)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_AnnAssign(self, node):
        if node.annotation is not None:
            self._use_words_in_strings(node.annotation)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                self._use_words_in_strings(node.value)
        self.generic_visit(node)


def analyze_source(source, filename="<string>"):
    """Return (unused, error). unused is a list of UnusedImport.

    error is None on success, else a string describing a parse failure.
    """
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return [], "SyntaxError: %s (line %d)" % (exc.msg, exc.lineno or 0)
    collector = _ImportCollector()
    collector.visit(tree)
    unused = []
    for imp in collector.imports:
        if imp["type_checking"]:
            continue
        if imp["name"] not in collector.used:
            unused.append(UnusedImport(imp["name"], imp["lineno"],
                                       imp["end_lineno"], imp["statement"],
                                       imp["module"]))
    return unused, None


def analyze_file(path):
    """Return (unused, error) for one file on disk."""
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return analyze_source(handle.read(), filename=path)


def is_python_file(path):
    return path.endswith(".py")


def iter_python_files(paths, exclude=(), include_init=False):
    """Yield .py files under the given files/directories.

    Skips __init__.py by default (its imports are usually re-exports),
    hidden/venv/build directories, and anything matching an --exclude
    substring.
    """
    exclude = list(exclude)
    seen = []
    for root in paths:
        if os.path.isfile(root):
            if is_python_file(root):
                seen.append(root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in SKIP_DIRS and d not in exclude
                           and not any(e in d for e in exclude)]
            for name in sorted(filenames):
                if not is_python_file(name):
                    continue
                if name == "__init__.py" and not include_init:
                    continue
                full = os.path.join(dirpath, name)
                if any(e in full for e in exclude):
                    continue
                seen.append(full)
    return seen


def _split_import_parts(text):
    """Split a comma-separated import list, keeping `as` aliases."""
    return [part.strip() for part in text.split(",") if part.strip()]


def apply_fix(path, unused):
    """Remove unused names from single-line import statements in `path`.

    Returns (fixed_count, skipped_count). Multi-line (parenthesised)
    import statements are left untouched and counted as skipped, so a
    fix never rewrites a statement it cannot parse safely.
    """
    by_line = {}
    for item in unused:
        if item.end_lineno != item.lineno:
            continue  # multi-line statement: do not touch
        by_line.setdefault(item.lineno, set()).add(item.name)

    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()

    fixed, skipped = 0, 0
    for item in unused:
        if item.end_lineno != item.lineno:
            skipped += 1

    new_lines = []
    for number, line in enumerate(lines, start=1):
        names = by_line.get(number)
        if not names:
            new_lines.append(line)
            continue
        stripped = line.strip()
        # Split off a trailing comment, keeping it for re-attachment.
        comment = ""
        if " #" in line:
            code, comment = line.split(" #", 1)
            comment = " #" + comment
        else:
            code = line
        indent = code[:len(code) - len(code.lstrip())]
        ending = chr(10) if line.endswith(chr(10)) else ""
        head = code.strip()
        if head.startswith("import "):
            parts = _split_import_parts(head[len("import "):])
            kept = [p for p in parts if _bound_name_from_part(p) not in names]
            fixed += len(parts) - len(kept)
            if kept:
                new_lines.append(indent + "import " + ", ".join(kept) + comment + ending)
            # else: whole line was unused imports -> drop the line
        elif head.startswith("from ") and " import " in head:
            before, after = head.split(" import ", 1)
            parts = _split_import_parts(after)
            kept = [p for p in parts if _bound_name_from_part(p) not in names]
            fixed += len(parts) - len(kept)
            if kept:
                new_lines.append(indent + before + " import " + ", ".join(kept)
                                 + comment + ending)
            # else: drop the line
        else:  # pragma: no cover - defensive; AST lines are import lines
            new_lines.append(line)

    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(new_lines)
    return fixed, skipped


def _bound_name_from_part(part):
    """Bound name of one `import a` / `a as b` / `a.b` list element."""
    part = part.strip()
    if " as " in part:
        return part.split(" as ", 1)[1].strip()
    return part.split(".")[0].strip()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="py-unused",
        description="Find unused imports in Python files (stdlib only).")
    parser.add_argument("paths", nargs="*", default=["."],
                        help="files or directories to scan (default: .)")
    parser.add_argument("--exclude", action="append", default=[],
                        metavar="PATTERN",
                        help="skip any path containing PATTERN (repeatable)")
    parser.add_argument("--json", action="store_true",
                        help="print results as JSON")
    parser.add_argument("--fix", action="store_true",
                        help="remove unused imports from single-line "
                             "import statements (in place)")
    parser.add_argument("--include-init", action="store_true",
                        help="also scan __init__.py files (skipped by "
                             "default: their imports are usually re-exports)")
    parser.add_argument("--version", action="version",
                        version="py-unused " + VERSION)
    args = parser.parse_args(argv)

    files = iter_python_files(args.paths, exclude=args.exclude,
                              include_init=args.include_init)
    if not files:
        print("py-unused: no Python files found under %s"
              % ", ".join(args.paths), file=sys.stderr)
        return 2

    all_unused = []   # (path, UnusedImport)
    errors = []       # (path, message)
    for path in files:
        unused, error = analyze_file(path)
        if error is not None:
            errors.append((path, error))
            continue
        for item in unused:
            all_unused.append((path, item))

    if args.fix and all_unused:
        per_file = {}
        for path, item in all_unused:
            per_file.setdefault(path, []).append(item)
        total_fixed, total_skipped = 0, 0
        for path, items in per_file.items():
            fixed, skipped = apply_fix(path, items)
            total_fixed += fixed
            total_skipped += skipped
        print("py-unused: removed %d unused import(s) from %d file(s)"
              % (total_fixed, len(per_file)))
        if total_skipped:
            print("py-unused: left %d multi-line import(s) untouched "
                  "(edit by hand)" % total_skipped)
        return 0

    if args.json:
        print(json.dumps(
            [{"file": p, "line": i.lineno, "name": i.name,
              "statement": i.statement, "module": i.module}
             for p, i in all_unused], indent=2))
    else:
        for path, item in all_unused:
            print("%s:%d: %r is imported but never used (%s)"
                  % (path, item.lineno, item.name, item.statement))

    for path, error in errors:
        print("%s: could not parse (%s)" % (path, error), file=sys.stderr)

    if errors:
        print("py-unused: %d file(s) could not be parsed; "
              "results above cover the rest" % len(errors), file=sys.stderr)
    if not all_unused:
        print("py-unused: no unused imports in %d file(s)" % len(files))
        return 0
    print("py-unused: %d unused import(s) in %d file(s)"
          % (len(all_unused), len({p for (p, _) in all_unused})))
    return 1


if __name__ == "__main__":
    sys.exit(main())
