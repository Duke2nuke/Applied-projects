#!/usr/bin/env python3
"""Tests for duplicate_finder.py. Run: python3 test_duplicate_finder.py"""

import os
import tempfile
import unittest

from duplicate_finder import find_duplicates


def write(root, rel, content):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return path


class TestDuplicateFinder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_identical_files_grouped_across_folders(self):
        write(self.root, "a.txt", b"same content here")
        write(self.root, "sub/b.txt", b"same content here")
        write(self.root, "c.txt", b"something else entirely")
        groups, summary = find_duplicates(self.root)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["files"]), 2)
        self.assertEqual(summary["duplicate_files"], 1)
        self.assertEqual(summary["wasted_bytes"], len(b"same content here"))

    def test_same_size_different_content_not_grouped(self):
        # Same length, different bytes: size grouping alone must not lie.
        write(self.root, "a.txt", b"abcdefgh")
        write(self.root, "b.txt", b"ijklmnop")
        groups, _ = find_duplicates(self.root)
        self.assertEqual(groups, [])

    def test_min_size_filters_small_files(self):
        write(self.root, "a.txt", b"tiny")
        write(self.root, "b.txt", b"tiny")
        groups, _ = find_duplicates(self.root, min_size=100)
        self.assertEqual(groups, [])

    def test_exclude_pattern_skips_files(self):
        write(self.root, "a.log", b"repeated")
        write(self.root, "b.log", b"repeated")
        groups, _ = find_duplicates(self.root, exclude=["*.log"])
        self.assertEqual(groups, [])

    def test_empty_files_skipped_by_default_included_with_flag(self):
        write(self.root, "empty1.txt", b"")
        write(self.root, "empty2.txt", b"")
        groups, _ = find_duplicates(self.root)
        self.assertEqual(groups, [])
        groups, _ = find_duplicates(self.root, include_empty=True)
        self.assertEqual(len(groups), 1)

    def test_wasted_bytes_counts_extra_copies_only(self):
        write(self.root, "a.bin", b"x" * 100)
        write(self.root, "b.bin", b"x" * 100)
        write(self.root, "c.bin", b"x" * 100)
        _, summary = find_duplicates(self.root)
        self.assertEqual(summary["wasted_bytes"], 200)  # keep 1, drop 2


if __name__ == "__main__":
    unittest.main(verbosity=2)
