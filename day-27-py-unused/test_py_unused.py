"""Tests for py-unused. Run: python -m unittest test_py_unused -v"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from py_unused import (analyze_source, analyze_file, apply_fix,
                       iter_python_files, main)


def unused_names(source):
    unused, error = analyze_source(source)
    assert error is None, error
    return sorted(item.name for item in unused)


class TestDetection(unittest.TestCase):
    def test_plain_unused_import_flagged(self):
        self.assertEqual(unused_names("import os\nprint('hi')\n"), ["os"])

    def test_used_import_not_flagged(self):
        self.assertEqual(unused_names("import os\nprint(os.getcwd())\n"), [])

    def test_attribute_use_counts(self):
        self.assertEqual(
            unused_names("import os.path\nprint(os.path.join('a', 'b'))\n"),
            [])

    def test_aliased_import(self):
        self.assertEqual(
            unused_names("import numpy as np\nprint(np.zeros(3))\n"), [])
        self.assertEqual(unused_names("import numpy as np\nprint(1)\n"),
                         ["np"])

    def test_from_import(self):
        self.assertEqual(
            unused_names("from collections import Counter\nprint(Counter())\n"),
            [])
        self.assertEqual(
            unused_names("from collections import Counter, defaultdict\n"
                         "print(Counter())\n"),
            ["defaultdict"])

    def test_from_import_alias(self):
        self.assertEqual(
            unused_names("from pathlib import Path as P\nprint(P('.'))\n"), [])
        self.assertEqual(
            unused_names("from pathlib import Path as P\nprint(1)\n"), ["P"])

    def test_star_import_skipped(self):
        # We cannot know which names a star import provides.
        self.assertEqual(unused_names("from os import *\nprint(1)\n"), [])

    def test_future_import_skipped(self):
        self.assertEqual(
            unused_names("from __future__ import annotations\nprint(1)\n"),
            [])

    def test_type_checking_import_skipped(self):
        src = ("from typing import TYPE_CHECKING\n"
               "if TYPE_CHECKING:\n"
               "    from expensive import Thing\n"
               "print(1)\n")
        self.assertEqual(unused_names(src), [])

    def test_all_uses_name(self):
        src = ("from m import Helper\n"
               "__all__ = ['Helper']\n")
        self.assertEqual(unused_names(src), [])

    def test_string_annotation_uses_name(self):
        src = ('from models import User\n'
               'def f(x: "User"):\n'
               '    return x\n')
        self.assertEqual(unused_names(src), [])

    def test_relative_import(self):
        self.assertEqual(
            unused_names("from . import helpers\nprint(helpers)\n"), [])
        self.assertEqual(unused_names("from . import helpers\nprint(1)\n"),
                         ["helpers"])

    def test_syntax_error_reported_not_raised(self):
        unused, error = analyze_source("import os\ndef broken(:\n")
        self.assertEqual(unused, [])
        self.assertIn("SyntaxError", error)

    def test_docstring_mention_is_not_a_use(self):
        src = ('"""Uses the os module for everything."""\n'
               "import os\nprint(1)\n")
        self.assertEqual(unused_names(src), ["os"])

    def test_plain_string_literal_is_not_a_use(self):
        src = 'import os\nx = "os"\nprint(x)\n'
        self.assertEqual(unused_names(src), ["os"])

    def test_multiple_unused_in_one_file(self):
        src = "import os\nimport sys\nimport json\nprint(os.getcwd())\n"
        self.assertEqual(unused_names(src), ["json", "sys"])


class TestFileDiscovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "pkg"))
        open(os.path.join(self.tmp, "a.py"), "w").write("import os\n")
        open(os.path.join(self.tmp, "pkg", "__init__.py"), "w").write(
            "from .core import thing\n")
        open(os.path.join(self.tmp, "pkg", "core.py"), "w").write("x = 1\n")
        open(os.path.join(self.tmp, "notes.txt"), "w").write("not code\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_init_skipped_by_default(self):
        files = iter_python_files([self.tmp])
        self.assertEqual(sorted(os.path.basename(f) for f in files),
                         ["a.py", "core.py"])

    def test_init_included_with_flag(self):
        files = iter_python_files([self.tmp], include_init=True)
        self.assertIn("__init__.py",
                      [os.path.basename(f) for f in files])

    def test_exclude_pattern(self):
        files = iter_python_files([self.tmp], exclude=["pkg"])
        self.assertEqual([os.path.basename(f) for f in files], ["a.py"])


class TestFix(unittest.TestCase):
    def _fix(self, source):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
        tmp.write(source)
        tmp.close()
        unused, error = analyze_file(tmp.name)
        self.assertIsNone(error)
        fixed, skipped = apply_fix(tmp.name, unused)
        with open(tmp.name) as handle:
            result = handle.read()
        os.unlink(tmp.name)
        return result, fixed, skipped

    def test_fix_removes_single_unused_name(self):
        result, fixed, _ = self._fix(
            "import os, sys\nprint(os.getcwd())\n")
        self.assertEqual(result, "import os\nprint(os.getcwd())\n")
        self.assertEqual(fixed, 1)

    def test_fix_drops_whole_line_when_all_unused(self):
        result, fixed, _ = self._fix("import os\nimport sys\nprint(1)\n")
        self.assertEqual(result, "print(1)\n")
        self.assertEqual(fixed, 2)

    def test_fix_from_import_keeps_used_name(self):
        result, fixed, _ = self._fix(
            "from collections import Counter, defaultdict\n"
            "print(Counter())\n")
        self.assertEqual(result,
                         "from collections import Counter\nprint(Counter())\n")
        self.assertEqual(fixed, 1)

    def test_fix_keeps_alias(self):
        result, fixed, _ = self._fix(
            "import numpy as np, os\nprint(np.zeros(1))\n")
        self.assertEqual(result,
                         "import numpy as np\nprint(np.zeros(1))\n")
        self.assertEqual(fixed, 1)

    def test_fix_skips_multiline_import(self):
        src = ("from collections import (\n"
               "    Counter,\n"
               "    defaultdict,\n"
               ")\n"
               "print(Counter())\n")
        result, fixed, skipped = self._fix(src)
        self.assertEqual(result, src)  # untouched
        self.assertEqual(fixed, 0)
        self.assertEqual(skipped, 1)


class TestCLI(unittest.TestCase):
    def test_exit_zero_when_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "clean.py")
            open(path, "w").write("import os\nprint(os.getcwd())\n")
            self.assertEqual(main([path]), 0)

    def test_exit_one_when_unused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "messy.py")
            open(path, "w").write("import os\nprint(1)\n")
            self.assertEqual(main([path]), 1)

    def test_exit_two_when_no_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main([tmp]), 2)


if __name__ == "__main__":
    unittest.main()
