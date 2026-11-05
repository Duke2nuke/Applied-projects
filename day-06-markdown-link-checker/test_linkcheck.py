"""Tests for linkcheck.py — run with: python -m unittest test_linkcheck -v"""

import tempfile
import unittest
from pathlib import Path

import linkcheck


def write(tmp: Path, name: str, text: str) -> Path:
    path = tmp / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class TestLinkcheck(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_good_and_broken_local_links(self):
        write(self.tmp, "guide.md", "# Guide\n")
        source = write(self.tmp, "a.md", "[ok](guide.md) [bad](missing.md)\n")
        report = linkcheck.run([str(self.tmp)])
        by_target = {r["target"]: r["status"] for r in report["results"]}
        self.assertEqual(by_target["guide.md"], "OK")
        self.assertEqual(by_target["missing.md"], "BROKEN")
        self.assertEqual(report["broken_count"], 1)

    def test_anchor_checked_against_headings(self):
        source = write(self.tmp, "a.md",
                       "# Title\n\n[ok](#title) [bad](#nope)\n")
        report = linkcheck.run([str(source)])
        by_target = {r["target"]: r["status"] for r in report["results"]}
        self.assertEqual(by_target["#title"], "OK")
        self.assertEqual(by_target["#nope"], "BROKEN")

    def test_links_in_code_blocks_are_ignored(self):
        write(self.tmp, "a.md", "```\n[bad](missing.md)\n```\n")
        report = linkcheck.run([str(self.tmp)])
        self.assertEqual(report["total"], 0)

    def test_remote_unchecked_without_flag(self):
        write(self.tmp, "a.md", "[web](https://example.com)\n")
        report = linkcheck.run([str(self.tmp)])
        self.assertEqual(report["results"][0]["status"], "UNCHECKED")
        self.assertEqual(report["broken_count"], 0)

    def test_mailto_skipped(self):
        write(self.tmp, "a.md", "[mail](mailto:someone@example.com)\n")
        report = linkcheck.run([str(self.tmp)])
        self.assertEqual(report["results"][0]["status"], "SKIPPED")


if __name__ == "__main__":
    unittest.main()
