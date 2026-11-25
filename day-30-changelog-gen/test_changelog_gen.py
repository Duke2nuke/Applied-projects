"""Tests for changelog_gen.py.

Each test builds a small real git repo in a temp dir (fixed author dates
so output is deterministic) and runs the generator against it.
"""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import changelog_gen  # noqa: E402


def git(repo, *args, env_extra=None):
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_DATE": "2026-11-20T10:00:00+05:30",
        "GIT_COMMITTER_DATE": "2026-11-20T10:00:00+05:30",
    })
    if env_extra:
        env.update(env_extra)
    subprocess.run(["git", "-C", repo] + list(args), check=True,
                   capture_output=True, text=True, env=env)


class FixtureRepo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "Test User")
        git(self.repo, "config", "user.email", "test@example.com")

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, message, fname="file.txt", body=None):
        path = os.path.join(self.repo, fname)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(message + "\n")
        git(self.repo, "add", ".")
        args = ["commit", "--allow-empty", "-m", message]
        if body:
            args += ["-m", body]
        git(self.repo, *args)

    def tag(self, name):
        git(self.repo, "tag", name)


class TestChangelogGen(FixtureRepo):
    def test_groups_features_and_fixes_under_tag(self):
        self.commit("feat: add dark mode")
        self.commit("fix: crash on empty input")
        self.commit("docs: update install steps")
        self.tag("v0.1.0")
        out = changelog_gen.generate(self.repo)
        self.assertIn("## [v0.1.0] - 2026-11-20", out)
        self.assertIn("### Features", out)
        self.assertIn("- add dark mode (", out)
        self.assertIn("### Bug Fixes", out)
        self.assertIn("- crash on empty input (", out)
        self.assertIn("### Documentation", out)
        self.assertNotIn("## [Unreleased]", out)

    def test_commits_after_tag_go_to_unreleased(self):
        self.commit("feat: first feature")
        self.tag("v0.1.0")
        self.commit("feat: second feature")
        out = changelog_gen.generate(self.repo)
        self.assertIn("## [Unreleased]", out)
        # Unreleased comes before the tagged release.
        self.assertLess(out.index("[Unreleased]"), out.index("[v0.1.0]"))
        unreleased = out.split("## [v0.1.0]")[0]
        self.assertIn("second feature", unreleased)
        self.assertNotIn("first feature", unreleased)

    def test_breaking_change_flag(self):
        self.commit("feat!: drop Python 3.8 support")
        out = changelog_gen.generate(self.repo)
        self.assertIn("### Breaking Changes", out)
        self.assertIn("drop Python 3.8 support", out)
        # A breaking entry is listed once, under Breaking Changes.
        self.assertNotIn("### Features", out)

    def test_breaking_change_in_body(self):
        self.commit("fix: change config format",
                    body="BREAKING CHANGE: old config files no longer load")
        out = changelog_gen.generate(self.repo)
        self.assertIn("### Breaking Changes", out)
        self.assertIn("change config format", out)

    def test_non_conventional_subject_goes_to_other(self):
        self.commit("tweaked the thing")
        out = changelog_gen.generate(self.repo)
        self.assertIn("### Other Changes", out)
        self.assertIn("- tweaked the thing (", out)

    def test_scope_rendered(self):
        self.commit("feat(auth): add login page")
        out = changelog_gen.generate(self.repo)
        self.assertIn("- **auth:** add login page (", out)

    def test_merge_commits_skipped_by_default(self):
        self.commit("feat: base work")
        self.commit("Merge branch 'other' into main")
        out = changelog_gen.generate(self.repo)
        self.assertNotIn("Merge branch", out)
        out2 = changelog_gen.generate(self.repo, include_merges=True)
        self.assertIn("Merge branch", out2)

    def test_since_filters_older_releases(self):
        self.commit("feat: old feature")
        self.tag("v0.1.0")
        self.commit("feat: new feature")
        self.tag("v0.2.0")
        out = changelog_gen.generate(self.repo, since="v0.1.0")
        self.assertIn("[v0.2.0]", out)
        self.assertNotIn("[v0.1.0]", out)
        self.assertNotIn("old feature", out)
        self.assertIn("new feature", out)

    def test_since_unknown_tag_raises(self):
        self.commit("feat: something")
        with self.assertRaises(changelog_gen.ChangelogError):
            changelog_gen.generate(self.repo, since="v9.9.9")

    def test_not_a_git_repo_raises(self):
        with tempfile.TemporaryDirectory() as plain:
            with self.assertRaises(changelog_gen.ChangelogError):
                changelog_gen.generate(plain)

    def test_empty_repo_raises(self):
        with self.assertRaises(changelog_gen.ChangelogError):
            changelog_gen.generate(self.repo)

    def test_output_file_written(self):
        self.commit("feat: write me out")
        target = os.path.join(self.repo, "CHANGELOG.md")
        rc = changelog_gen.main(["--repo", self.repo, "--output", target])
        self.assertEqual(rc, 0)
        with open(target, encoding="utf-8") as fh:
            self.assertIn("write me out", fh.read())

    def test_main_returns_2_on_error(self):
        with tempfile.TemporaryDirectory() as plain:
            rc = changelog_gen.main(["--repo", plain])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
