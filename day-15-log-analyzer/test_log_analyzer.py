"""Tests for log_analyzer.py — run with: python -m pytest test_log_analyzer.py -v
(or: python test_log_analyzer.py)"""

import io
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from log_analyzer import (  # noqa: E402
    analyse,
    format_text,
    main,
    parse_access_line,
    parse_plain_line,
    report_dict,
)

ACCESS_LINES = [
    '203.0.113.7 - - [10/Nov/2026:08:00:01 +0530] "GET / HTTP/1.1" 200 512 "-" "curl/8.0" 0.012',
    '198.51.100.23 - - [10/Nov/2026:08:00:02 +0530] "POST /api/login HTTP/1.1" 401 96 "-" "python-requests/2.31" 0.009',
    '192.0.2.55 - - [10/Nov/2026:08:00:03 +0530] "GET /old-page HTTP/1.1" 404 151 "-" "Mozilla/5.0" 0.004',
    '203.0.113.7 - - [10/Nov/2026:08:00:04 +0530] "GET /api/reports HTTP/1.1" 500 210 "-" "curl/8.0" 1.284',
    '203.0.113.7 - - [10/Nov/2026:08:00:05 +0530] "GET /api/reports HTTP/1.1" 200 90210 "-" "curl/8.0" 0.872',
]

PLAIN_LINES = [
    "2026-11-10 08:00:01 INFO server started",
    "2026-11-10 08:00:02 WARN slow query on /api/reports",
    "2026-11-10 08:00:03 ERROR database connection lost",
    "2026-11-10 08:00:04 ERROR unhandled exception in /api/reports",
    "2026-11-10 08:00:05 DEBUG cache miss",
]


def test_parse_access_line_fields():
    entry = parse_access_line(ACCESS_LINES[0])
    assert entry is not None
    assert entry.ip == "203.0.113.7"
    assert entry.method == "GET"
    assert entry.path == "/"
    assert entry.status == 200
    assert entry.size == 512
    assert entry.rt == 0.012


def test_parse_access_line_rejects_garbage():
    assert parse_access_line("not a log line at all") is None
    assert parse_access_line("") is None
    assert parse_access_line("2026-11-10 INFO hello") is None


def test_parse_plain_line_levels():
    assert parse_plain_line("2026-11-10 08:00:01 INFO started") == "INFO"
    assert parse_plain_line("2026-11-10 08:00:02 WARNING disk 90% full") == "WARN"
    assert parse_plain_line("2026-11-10 08:00:03 ERROR boom") == "ERROR"
    assert parse_plain_line("just a sentence with no level") is None


def test_status_breakdown_and_error_rate():
    report = analyse(ACCESS_LINES)
    assert report.access_parsed == 5
    assert report.status_codes[200] == 2
    assert report.status_codes[401] == 1
    assert report.status_codes[404] == 1
    assert report.status_codes[500] == 1
    assert report.status_classes["2xx"] == 2
    assert report.status_classes["4xx"] == 2
    assert report.status_classes["5xx"] == 1
    assert report.error_rate == 0.6  # 3 of 5 are 4xx/5xx


def test_top_paths_ips_and_error_paths():
    report = analyse(ACCESS_LINES)
    assert report.paths["/api/reports"] == 2
    assert report.ips["203.0.113.7"] == 3
    assert report.error_paths["/old-page"] == 1
    assert report.error_paths["/api/login"] == 1


def test_slowest_requests_sorted():
    report = analyse(ACCESS_LINES)
    assert report.slowest[0][0] == 1.284  # /api/reports 500
    assert report.slowest[0][2] == "/api/reports"
    assert report.slowest[1][0] == 0.872


def test_plain_log_levels_and_error_lines():
    report = analyse(PLAIN_LINES)
    assert report.plain_parsed == 5
    assert report.access_parsed == 0
    assert report.level_counts["ERROR"] == 2
    assert report.level_counts["WARN"] == 1
    assert report.level_counts["INFO"] == 1
    assert len(report.error_lines) == 2
    assert report.error_lines[0][0] == 3  # 1-based line number
    assert "database connection lost" in report.error_lines[0][1]


def test_mixed_file_and_unparsed_lines():
    lines = ACCESS_LINES + PLAIN_LINES + ["~~~ garbage ~~~", "another odd line"]
    report = analyse(lines)
    assert report.total == 12
    assert report.access_parsed == 5
    assert report.plain_parsed == 5
    assert report.unparsed == 2


def test_report_dict_is_json_serialisable():
    report = analyse(ACCESS_LINES + PLAIN_LINES)
    payload = report_dict(report)
    text = json.dumps(payload)  # must not raise
    assert json.loads(text)["total_lines"] == 10
    assert payload["error_rate"] == 0.6


def test_cli_on_example_files(tmp_path):
    for name in ("access.log", "app.log"):
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "example", name)
        out = subprocess.run(
            [sys.executable, "log_analyzer.py", src],
            capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        assert out.returncode == 0, out.stderr
        assert "LogLens report" in out.stdout
    out = subprocess.run(
        [sys.executable, "log_analyzer.py", "example/access.log",
         "--json", str(tmp_path / "report.json")],
        capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    assert out.returncode == 0, out.stderr
    data = json.loads((tmp_path / "report.json").read_text())
    assert data["total_lines"] == 12
    assert data["status_codes"]["404"] == 4


def test_cli_missing_file_returns_2():
    assert main(["/definitely/not/a/real.log"]) == 2


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
