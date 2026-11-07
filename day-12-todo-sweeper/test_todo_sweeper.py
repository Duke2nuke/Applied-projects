#!/usr/bin/env python3
"""Tests for todo_sweeper.py. Run: python3 test_todo_sweeper.py"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import todo_sweeper  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "todo_sweeper.py")


def write_tree(root, files):
    for rel, content in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(path, mode) as fh:
            fh.write(content)


class TestSweeper(unittest.TestCase):
    def test_all_six_tags_detected(self):
        with tempfile.TemporaryDirectory() as root:
            write_tree(root, {"a.py": (
                "# TODO: add validation\n"
                "# FIXME: off-by-one here\n"
                "# HACK: works around the API bug\n"
                "# XXX: why does this return None?\n"
                "# NOTE: keep this in sync with docs\n"
                "# BUG: crashes on empty input\n")})
            markers, scanned, _ = todo_sweeper.sweep(root, set(todo_sweeper.TAGS), [], (), False)
            self.assertEqual(scanned, 1)
            self.assertEqual(len(markers), 6)
            self.assertEqual(sorted(m["tag"] for m in markers),
                             ["BUG", "FIXME", "HACK", "NOTE", "TODO", "XXX"])
            todo = next(m for m in markers if m["tag"] == "TODO")
            self.assertEqual((todo["file"], todo["line"]), ("a.py", 1))
            self.assertEqual(todo["text"], "TODO: add validation")

    def test_owner_and_comment_styles(self):
        with tempfile.TemporaryDirectory() as root:
            write_tree(root, {"b.js": (
                "// TODO(alice): rewrite this\n"
                "/* FIXME: leaks memory */\n"
                "<!-- NOTE: update the banner -->\n")})
            markers, _, _ = todo_sweeper.sweep(root, set(todo_sweeper.TAGS), [], (), False)
            self.assertEqual(len(markers), 3)
            todo = next(m for m in markers if m["tag"] == "TODO")
            self.assertEqual(todo["owner"], "alice")
            fixme = next(m for m in markers if m["tag"] == "FIXME")
            self.assertEqual(fixme["text"], "FIXME: leaks memory")
            note = next(m for m in markers if m["tag"] == "NOTE")
            self.assertEqual(note["text"], "NOTE: update the banner")

    def test_no_false_positives_on_similar_words(self):
        with tempfile.TemporaryDirectory() as root:
            write_tree(root, {"c.py": (
                "# TODOLIST = []\n"
                "# This method fixes the bug.\n"
                "# notedown the result\n"
                "print('TODO')  # a string literal, not a marker\n")})
            markers, _, _ = todo_sweeper.sweep(root, set(todo_sweeper.TAGS), [], (), False)
            # TODOLIST / "fixes the bug" / "notedown" / quoted 'TODO'
            # are prose or code, not comment markers — none may match.
            self.assertEqual(markers, [])

    def test_mid_line_and_bare_markers(self):
        with tempfile.TemporaryDirectory() as root:
            write_tree(root, {"e.py": (
                "x = 1  # TODO: fix later\n"
                "TODO: bare marker at line start\n")})
            markers, _, _ = todo_sweeper.sweep(root, set(todo_sweeper.TAGS), [], (), False)
            self.assertEqual(len(markers), 2)
            self.assertEqual([m["line"] for m in markers], [1, 2])

    def test_skips_git_binary_and_excluded(self):
        with tempfile.TemporaryDirectory() as root:
            write_tree(root, {
                ".git/config": "# TODO: never scanned\n",
                "bin.dat": b"\x00\x01TODO: binary junk\n",
                "skip.log": "# TODO: excluded by pattern\n",
                "real.py": "# TODO: the only real one\n",
            })
            markers, scanned, skipped = todo_sweeper.sweep(
                root, set(todo_sweeper.TAGS), ["*.log"], (), False)
            self.assertEqual(len(markers), 1)
            self.assertEqual(markers[0]["file"], "real.py")
            self.assertEqual(scanned, 1)
            self.assertGreaterEqual(skipped, 2)  # .git dir + binary + .log

    def test_tag_filter_and_json_output(self):
        with tempfile.TemporaryDirectory() as root:
            write_tree(root, {"d.py": "# TODO: one\n# FIXME: two\n"})
            markers, _, _ = todo_sweeper.sweep(root, {"FIXME"}, [], (), False)
            self.assertEqual([m["tag"] for m in markers], ["FIXME"])
            out = subprocess.run(
                [sys.executable, SCRIPT, root, "--json"],
                capture_output=True, text=True, check=False)
            self.assertEqual(out.returncode, 1)  # markers found
            data = json.loads(out.stdout)
            self.assertEqual(data["markers_found"], 2)
            self.assertEqual(data["by_tag"], {"FIXME": 1, "TODO": 1})

    def test_exit_code_zero_on_clean_tree(self):
        with tempfile.TemporaryDirectory() as root:
            write_tree(root, {"clean.py": "print('all done')\n"})
            out = subprocess.run(
                [sys.executable, SCRIPT, root],
                capture_output=True, text=True, check=False)
            self.assertEqual(out.returncode, 0)
            self.assertIn("Clean", out.stdout)
            bad = subprocess.run(
                [sys.executable, SCRIPT, os.path.join(root, "nope")],
                capture_output=True, text=True, check=False)
            self.assertEqual(bad.returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
