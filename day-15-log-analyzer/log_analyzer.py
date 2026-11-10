#!/usr/bin/env python3
"""LogLens — a small, dependency-free log-file analyser.

Reads a web-server access log (Apache/Nginx combined format, with an
optional trailing response-time field) and/or a plain-text application
log, and prints a human-readable summary:

  * total lines, how many parsed as access lines / plain log lines,
    and how many could not be parsed at all
  * status-code breakdown by class (2xx / 3xx / 4xx / 5xx) and the
    individual codes, for access lines
  * most-requested paths and most-active client IPs
  * paths that produced the most 4xx/5xx errors
  * slowest requests (when a response-time field is present)
  * ERROR / WARN / INFO counts and the actual error lines, for
    plain-text logs

Usage:
    python log_analyzer.py access.log
    python log_analyzer.py app.log --top 5
    python log_analyzer.py access.log --json report.json
    python log_analyzer.py app.log --errors-only

Exit codes: 0 = ok, 2 = usage / unreadable file.
"""

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field


# 203.0.113.7 - - [10/Nov/2026:08:00:01 +0530] "GET /api/users HTTP/1.1"
# 200 512 "-" "curl/8.0" 0.042
ACCESS_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>[A-Z]+) (?P<path>\S+) (?P<proto>[^"]+)" '
    r'(?P<status>\d{3}) (?P<size>\S+)'
    r'(?: "(?P<referer>[^"]*)" "(?P<agent>[^"]*)")?'
    r'(?: (?P<rt>\d+(?:\.\d+)?))?$'
)

LEVEL_RE = re.compile(
    r'\b(?P<level>ERROR|WARN|WARNING|INFO|DEBUG|CRITICAL)\b'
)

# A line that is mostly "2026-11-10 08:00:01 ERROR something broke"
PLAIN_RE = re.compile(
    r'^(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?'
    r'(?:Z|[+-]\d{2}:?\d{2})?)?\s*'
    r'(?P<level>ERROR|WARN|WARNING|INFO|DEBUG|CRITICAL)?'
    r'[\s:\-\[\]]*(?P<msg>.*)$'
)


@dataclass
class AccessEntry:
    ip: str
    method: str
    path: str
    status: int
    size: int
    rt: float | None = None


@dataclass
class Report:
    total: int = 0
    access_parsed: int = 0
    plain_parsed: int = 0
    unparsed: int = 0
    status_codes: Counter = field(default_factory=Counter)
    status_classes: Counter = field(default_factory=Counter)
    paths: Counter = field(default_factory=Counter)
    ips: Counter = field(default_factory=Counter)
    error_paths: Counter = field(default_factory=Counter)
    slowest: list = field(default_factory=list)  # (rt, method, path, status)
    level_counts: Counter = field(default_factory=Counter)
    error_lines: list = field(default_factory=list)  # (lineno, text)

    @property
    def error_rate(self) -> float:
        """Share of access lines that were 4xx or 5xx (0 if none)."""
        total = self.access_parsed
        if not total:
            return 0.0
        bad = self.status_classes.get("4xx", 0) + self.status_classes.get("5xx", 0)
        return bad / total


def parse_access_line(line: str) -> AccessEntry | None:
    """Parse one combined-format access-log line; None if it does not fit."""
    m = ACCESS_RE.match(line.strip())
    if not m:
        return None
    try:
        size = int(m.group("size")) if m.group("size") != "-" else 0
        rt = float(m.group("rt")) if m.group("rt") else None
        return AccessEntry(
            ip=m.group("ip"),
            method=m.group("method"),
            path=m.group("path"),
            status=int(m.group("status")),
            size=size,
            rt=rt,
        )
    except ValueError:
        return None


def parse_plain_line(line: str) -> str | None:
    """Return the log level (ERROR/WARN/INFO/...) of a plain log line.

    Returns None when the line carries no recognisable level at all.
    """
    m = LEVEL_RE.search(line)
    if not m:
        return None
    level = m.group("level")
    return "WARN" if level == "WARNING" else level


def analyse(lines, top_n: int = 10) -> Report:
    """Analyse an iterable of log lines and return a Report."""
    report = Report()
    slowest_all: list = []
    for lineno, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        report.total += 1
        entry = parse_access_line(line)
        if entry is not None:
            report.access_parsed += 1
            report.status_codes[entry.status] += 1
            report.status_classes[f"{entry.status // 100}xx"] += 1
            report.paths[entry.path] += 1
            report.ips[entry.ip] += 1
            if entry.status >= 400:
                report.error_paths[entry.path] += 1
            if entry.rt is not None:
                slowest_all.append((entry.rt, entry.method, entry.path, entry.status))
            continue
        level = parse_plain_line(line)
        if level is not None:
            report.plain_parsed += 1
            report.level_counts[level] += 1
            if level in ("ERROR", "CRITICAL"):
                report.error_lines.append((lineno, line.strip()))
            continue
        report.unparsed += 1
    report.slowest = sorted(slowest_all, reverse=True)[:top_n]
    return report


def report_dict(report: Report, top_n: int = 10) -> dict:
    return {
        "total_lines": report.total,
        "access_lines": report.access_parsed,
        "plain_log_lines": report.plain_parsed,
        "unparsed_lines": report.unparsed,
        "error_rate": round(report.error_rate, 4),
        "status_codes": dict(sorted(report.status_codes.items())),
        "status_classes": dict(sorted(report.status_classes.items())),
        "top_paths": report.paths.most_common(top_n),
        "top_ips": report.ips.most_common(top_n),
        "top_error_paths": report.error_paths.most_common(top_n),
        "slowest_requests": [
            {"response_time_s": rt, "method": m, "path": p, "status": s}
            for rt, m, p, s in report.slowest
        ],
        "level_counts": dict(sorted(report.level_counts.items())),
        "error_lines": [
            {"line": n, "text": t} for n, t in report.error_lines
        ],
    }


def format_text(report: Report, top_n: int = 10) -> str:
    out = [f"LogLens report — {report.total} lines"]
    out.append(
        f"  access lines: {report.access_parsed}  "
        f"plain log lines: {report.plain_parsed}  "
        f"unparsed: {report.unparsed}"
    )
    if report.access_parsed:
        out.append(f"  error rate (4xx+5xx): {report.error_rate:.1%}")
        out.append("  status codes:")
        for code, count in sorted(report.status_codes.items()):
            out.append(f"    {code}: {count}")
        out.append(f"  top {top_n} paths:")
        for path, count in report.paths.most_common(top_n):
            out.append(f"    {count:>5}  {path}")
        out.append(f"  top {top_n} client IPs:")
        for ip, count in report.ips.most_common(top_n):
            out.append(f"    {count:>5}  {ip}")
        if report.error_paths:
            out.append("  paths with most errors:")
            for path, count in report.error_paths.most_common(top_n):
                out.append(f"    {count:>5}  {path}")
        if report.slowest:
            out.append("  slowest requests (seconds):")
            for rt, method, path, status in report.slowest:
                out.append(f"    {rt:>7.3f}s  {method} {path} -> {status}")
    if report.level_counts:
        out.append("  log levels:")
        for level, count in sorted(report.level_counts.items()):
            out.append(f"    {level}: {count}")
    if report.error_lines:
        out.append("  error lines:")
        for lineno, text in report.error_lines:
            out.append(f"    line {lineno}: {text[:160]}")
    if not report.access_parsed and not report.plain_parsed:
        out.append("  (nothing recognised — is this a log file?)")
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarise a web access log and/or plain-text app log."
    )
    parser.add_argument("logfile", help="path to the log file to analyse")
    parser.add_argument("--top", type=int, default=10,
                        help="how many entries to show in each top-N list (default 10)")
    parser.add_argument("--json", dest="json_out", metavar="FILE",
                        help="also write the full report as JSON to FILE")
    parser.add_argument("--errors-only", action="store_true",
                        help="print only the error lines, one per line")
    args = parser.parse_args(argv)

    try:
        with open(args.logfile, encoding="utf-8", errors="replace") as fh:
            report = analyse(fh, top_n=args.top)
    except OSError as exc:
        print(f"loglens: cannot read {args.logfile}: {exc}", file=sys.stderr)
        return 2

    if args.errors_only:
        for lineno, text in report.error_lines:
            print(f"{lineno}: {text}")
        return 0

    print(format_text(report, top_n=args.top))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(report_dict(report, top_n=args.top), fh, indent=2)
        print(f"\nJSON report written to {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
