#!/usr/bin/env python3
"""changelog-gen: generate a CHANGELOG.md from a git repository's history.

Reads `git log`, groups commits by release (git tags; anything newer than
the newest tag is "Unreleased"), and sorts each release's commits into
sections from their Conventional Commits subjects (feat:, fix:, docs:, ...).

Stdlib only. Requires git on PATH and a git repository as input.

Usage:
    python changelog_gen.py [--repo PATH] [--output FILE] [--since TAG]
                            [--title TITLE] [--include-merges]
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field

# Conventional-commit type -> CHANGELOG section heading.
TYPE_SECTIONS = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "docs": "Documentation",
    "refactor": "Refactoring",
    "perf": "Performance",
    "test": "Tests",
    "chore": "Chores",
    "build": "Build",
    "ci": "CI",
    "style": "Style",
    "revert": "Reverts",
}

SUBJECT_RE = re.compile(r"^([a-zA-Z]+)(\(([^)]+)\))?(!)?:\s+(.+)$")
BREAKING_RE = re.compile(r"^BREAKING[ -]CHANGE:\s*(.+)", re.MULTILINE)


class ChangelogError(Exception):
    """Raised when the changelog cannot be generated (bad repo, bad flag)."""


@dataclass
class Commit:
    sha: str
    author: str
    date: str
    subject: str
    body: str = ""


@dataclass
class Release:
    name: str  # e.g. "Unreleased" or "v1.1.0"
    date: str | None = None  # tag date, None for Unreleased
    sections: dict = field(default_factory=dict)  # heading -> [entry str]


def run_git(repo, args):
    """Run a git command in `repo`; return stdout or raise ChangelogError."""
    proc = subprocess.run(
        ["git", "-C", str(repo)] + args,
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise ChangelogError(
            f"git {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout


def get_commits(repo):
    """All commits, newest first, with subject and body."""
    fmt = "%H%x1f%an%x1f%ad%x1f%s%x1f%b%x1e"
    out = run_git(repo, ["log", f"--format={fmt}", "--date=short"])
    commits = []
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if not record.strip():
            continue
        parts = record.split("\x1f")
        if len(parts) != 5:
            continue
        sha, author, date, subject, body = parts
        commits.append(Commit(sha, author, date, subject, body.strip()))
    if not commits:
        raise ChangelogError("no commits found in this repository")
    return commits


def get_tags(repo):
    """Tags newest first: list of (tag name, tagged commit sha, tag date)."""
    out = run_git(repo, ["tag", "--sort=-creatordate",
                         "--format=%(refname:short)%09%(creatordate:short)"])
    tags = []
    for line in out.splitlines():
        if not line.strip():
            continue
        name, date = line.split("\t")
        sha = run_git(repo, ["rev-list", "-n", "1", name]).strip()
        tags.append((name, sha, date))
    return tags


def parse_subject(subject):
    """Split a Conventional Commits subject.

    Returns (section, scope, breaking, description). A non-conventional
    subject lands in "Other Changes" with the whole subject as description.
    """
    match = SUBJECT_RE.match(subject)
    if not match:
        return "Other Changes", None, False, subject
    ctype, _scope_group, scope, bang, description = match.groups()
    section = TYPE_SECTIONS.get(ctype.lower(), "Other Changes")
    return section, scope, bool(bang), description


def is_breaking(commit, subject_breaking):
    return subject_breaking or bool(BREAKING_RE.search(commit.body))


def format_entry(commit, scope, description):
    short = commit.sha[:7]
    if scope:
        return f"- **{scope}:** {description} ({short})"
    return f"- {description} ({short})"


def build_releases(commits, tags, include_merges=False, since=None):
    """Assign commits to releases, newest release first."""
    if since is not None and not any(name == since for name, _, _ in tags):
        raise ChangelogError(f"tag not found: {since}")

    releases = []
    unreleased = Release("Unreleased")
    releases.append(unreleased)
    tag_releases = {}
    for name, _sha, date in tags:
        rel = Release(name, date)
        tag_releases[name] = rel
        releases.append(rel)

    # Walk commits newest -> oldest. A commit belongs to the release of the
    # first tag (newest first) whose tagged commit we have reached.
    tag_index = 0  # index into tags, newest first
    current = unreleased
    for commit in commits:
        if commit.subject.startswith("Merge ") and not include_merges:
            continue
        while tag_index < len(tags) and commit.sha == tags[tag_index][1]:
            current = tag_releases[tags[tag_index][0]]
            tag_index += 1
        section, scope, subject_breaking, description = parse_subject(commit.subject)
        entry = format_entry(commit, scope, description)
        if is_breaking(commit, subject_breaking):
            current.sections.setdefault("Breaking Changes", []).append(entry)
        else:
            current.sections.setdefault(section, []).append(entry)

    releases = [r for r in releases if r.sections]
    if since is not None:
        # Keep Unreleased plus releases newer than `since`; drop `since`
        # itself and everything older.
        kept = []
        for rel in releases:
            if rel.name == "Unreleased":
                kept.append(rel)
            elif rel.name == since:
                break
            else:
                kept.append(rel)
        releases = kept
    return releases


SECTION_ORDER = [
    "Breaking Changes", "Features", "Bug Fixes", "Performance",
    "Refactoring", "Documentation", "Tests", "Build", "CI", "Style",
    "Reverts", "Chores", "Other Changes",
]


def render(releases, title="Changelog"):
    lines = [f"# {title}", "",
             "All notable changes to this project will be documented in this file.",
             ""]
    for rel in releases:
        heading = f"## [{rel.name}]"
        if rel.date:
            heading += f" - {rel.date}"
        lines.append(heading)
        lines.append("")
        for section in SECTION_ORDER:
            entries = rel.sections.get(section)
            if not entries:
                continue
            lines.append(f"### {section}")
            lines.append("")
            lines.extend(entries)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate(repo, since=None, include_merges=False, title="Changelog"):
    commits = get_commits(repo)
    tags = get_tags(repo)
    # Order tags by where their commit sits in the log (newest first).
    # Tag creation dates can tie (same-day releases), so log position --
    # not creatordate -- is the reliable ordering.
    position = {commit.sha: i for i, commit in enumerate(commits)}
    tags.sort(key=lambda tag: position.get(tag[1], len(commits)))
    releases = build_releases(commits, tags, include_merges, since)
    if not releases:
        raise ChangelogError("no changes to report (try without --since)")
    return render(releases, title)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a CHANGELOG.md from git history "
                    "(Conventional Commits, grouped by tag).")
    parser.add_argument("--repo", default=".",
                        help="path to the git repository (default: .)")
    parser.add_argument("--output", default=None,
                        help="write the changelog to this file "
                             "(default: print to stdout)")
    parser.add_argument("--since", default=None,
                        help="only include releases newer than this tag")
    parser.add_argument("--title", default="Changelog",
                        help="top-level heading (default: Changelog)")
    parser.add_argument("--include-merges", action="store_true",
                        help="include merge commits (skipped by default)")
    args = parser.parse_args(argv)

    try:
        text = generate(args.repo, since=args.since,
                        include_merges=args.include_merges, title=args.title)
    except ChangelogError as exc:
        print(f"changelog-gen: error: {exc}", file=sys.stderr)
        return 2
    except subprocess.TimeoutExpired:
        print("changelog-gen: error: git command timed out", file=sys.stderr)
        return 2

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {args.output}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
