"""dqcheck — a small CSV data-quality checker (stdlib only).

Profiles a CSV file column by column and flags the data-quality problems
that bite before training or analysis: missing values, constant or
fully-empty columns, duplicate rows, mixed types, outliers, invalid
emails and unparseable dates.

Usage:
    python dqcheck.py data.csv
    python dqcheck.py data.csv --json
    python dqcheck.py data.csv --fail-on warn   # exit 1 on warnings too

Exit codes: 0 = PASS, 1 = WARN (or FAIL when --fail-on warn), 2 = FAIL.
"""

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime

__version__ = "1.0.0"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MISSING_TOKENS = {"", "na", "n/a", "null", "none", "nan", "-"}
BOOL_TOKENS = {"true", "false", "yes", "no", "y", "n", "0", "1"}


def is_missing(value):
    """Treat blanks and common null spellings as missing."""
    return value is None or value.strip().lower() in MISSING_TOKENS


def _try_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _try_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _try_date(value):
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def classify_value(value):
    """Return the primitive kind of one non-missing cell value."""
    if _try_int(value) is not None:
        return "int"
    if _try_float(value) is not None:
        return "float"
    if _try_date(value) is not None:
        return "date"
    if value.strip().lower() in BOOL_TOKENS:
        return "bool"
    return "string"


def infer_type(kinds):
    """Collapse per-value kinds into one column type."""
    kinds = set(kinds)
    if not kinds:
        return "unknown"
    if kinds == {"int"}:
        return "int"
    if kinds <= {"int", "float"}:
        return "number"
    if len(kinds) == 1:
        return kinds.pop()
    return "mixed"


def _percentile(sorted_values, pct):
    if not sorted_values:
        return None
    index = (len(sorted_values) - 1) * pct
    lower = int(math.floor(index))
    upper = int(math.ceil(index))
    if lower == upper:
        return sorted_values[lower]
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def profile_column(name, values):
    """Profile one column; `values` are the raw strings, one per row."""
    total = len(values)
    non_missing = [v for v in values if not is_missing(v)]
    missing = total - len(non_missing)
    kinds = [classify_value(v) for v in non_missing]
    col_type = infer_type(kinds)
    unique = len(set(non_missing))

    profile = {
        "name": name,
        "rows": total,
        "missing": missing,
        "missing_pct": round(100.0 * missing / total, 1) if total else 0.0,
        "unique": unique,
        "type": col_type,
        "constant": unique == 1 and len(non_missing) > 0,
        "empty": len(non_missing) == 0,
    }

    if col_type in ("int", "number"):
        nums = sorted(float(v) for v in non_missing)
        mean = sum(nums) / len(nums)
        variance = sum((x - mean) ** 2 for x in nums) / len(nums)
        q1 = _percentile(nums, 0.25)
        q3 = _percentile(nums, 0.75)
        iqr = q3 - q1
        low = q1 - 1.5 * iqr
        high = q3 + 1.5 * iqr
        outliers = [x for x in nums if x < low or x > high]
        profile.update({
            "min": nums[0],
            "max": nums[-1],
            "mean": round(mean, 4),
            "median": _percentile(nums, 0.5),
            "stdev": round(math.sqrt(variance), 4),
            "outliers": len(outliers),
        })
    elif col_type == "string":
        profile["top_values"] = [
            {"value": value, "count": count}
            for value, count in Counter(non_missing).most_common(5)
        ]
    return profile


def check_csv(path, delimiter=None, missing_threshold=0.2):
    """Read a CSV and return the full quality report as a dict."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        if delimiter is None:
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
            except csv.Error:
                delimiter = ","
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError("empty CSV: no header row found")
        columns = list(reader.fieldnames)
        rows = list(reader)

    # csv.DictReader puts surplus fields under the None key; that is a
    # shape problem in the file itself, so surface it, not silently drop it.
    ragged = sum(1 for row in rows if None in row)

    row_count = len(rows)
    row_tuples = [tuple(row.get(col, "") for col in columns) for row in rows]
    duplicate_rows = row_count - len(set(row_tuples))

    issues = []
    if duplicate_rows:
        issues.append({
            "severity": "error",
            "column": None,
            "code": "duplicate_rows",
            "message": f"{duplicate_rows} duplicate row(s) "
                       f"({duplicate_rows}/{row_count} rows are extra copies)",
        })
    if ragged:
        issues.append({
            "severity": "error",
            "column": None,
            "code": "ragged_rows",
            "message": f"{ragged} row(s) have more fields than the header",
        })

    column_profiles = []
    for col in columns:
        values = [row.get(col) or "" for row in rows]
        profile = profile_column(col, values)
        column_profiles.append(profile)

        if profile["empty"]:
            issues.append({
                "severity": "error", "column": col, "code": "empty_column",
                "message": "column is completely empty",
            })
            continue
        if profile["type"] == "mixed":
            kinds = Counter(classify_value(v) for v in values
                            if not is_missing(v))
            issues.append({
                "severity": "error", "column": col, "code": "mixed_types",
                "message": "mixed value types: " + ", ".join(
                    f"{kind} x{count}" for kind, count in kinds.most_common()),
            })
        if profile["constant"]:
            issues.append({
                "severity": "warn", "column": col, "code": "constant_column",
                "message": f"constant value {values[0]!r} in every row — "
                           "carries no information",
            })
        if profile["missing_pct"] / 100.0 > missing_threshold:
            issues.append({
                "severity": "warn", "column": col, "code": "high_missing",
                "message": f"{profile['missing_pct']}% missing "
                           f"({profile['missing']} of {row_count} rows)",
            })
        if profile.get("outliers"):
            issues.append({
                "severity": "warn", "column": col, "code": "outliers",
                "message": f"{profile['outliers']} outlier(s) by the "
                           "1.5 x IQR rule",
            })
        if (profile["unique"] / max(row_count, 1) > 0.95
                and row_count > 10
                and "id" not in col.lower()):
            issues.append({
                "severity": "warn", "column": col, "code": "near_unique",
                "message": f"{profile['unique']} distinct values in "
                           f"{row_count} rows — looks like an ID column",
            })
        if "email" in col.lower():
            bad = [v for v in values
                   if not is_missing(v) and not EMAIL_RE.match(v.strip())]
            if bad:
                issues.append({
                    "severity": "warn", "column": col, "code": "invalid_email",
                    "message": f"{len(bad)} value(s) are not valid emails, "
                               f"e.g. {bad[0]!r}",
                })
        if "date" in col.lower() and profile["type"] not in ("date", "unknown"):
            bad = [v for v in values
                   if not is_missing(v) and _try_date(v.strip()) is None]
            if bad:
                issues.append({
                    "severity": "warn", "column": col, "code": "bad_date",
                    "message": f"{len(bad)} value(s) do not parse as dates, "
                               f"e.g. {bad[0]!r}",
                })

    errors = sum(1 for i in issues if i["severity"] == "error")
    warns = sum(1 for i in issues if i["severity"] == "warn")
    verdict = "FAIL" if errors else ("WARN" if warns else "PASS")

    return {
        "file": path,
        "rows": row_count,
        "columns": len(columns),
        "duplicate_rows": duplicate_rows,
        "ragged_rows": ragged,
        "total_missing_cells": sum(p["missing"] for p in column_profiles),
        "verdict": verdict,
        "error_count": errors,
        "warning_count": warns,
        "issues": issues,
        "column_profiles": column_profiles,
    }


def format_text(report):
    """Render the report as a human-readable text summary."""
    lines = [
        f"dqcheck {__version__} — {report['file']}",
        f"Rows: {report['rows']}  Columns: {report['columns']}  "
        f"Missing cells: {report['total_missing_cells']}  "
        f"Duplicate rows: {report['duplicate_rows']}",
        f"Verdict: {report['verdict']} "
        f"({report['error_count']} error(s), "
        f"{report['warning_count']} warning(s))",
        "",
        "Columns:",
    ]
    for profile in report["column_profiles"]:
        line = (f"  {profile['name']:<16} {profile['type']:<7} "
                f"missing {profile['missing_pct']:>5}%  "
                f"unique {profile['unique']}")
        if "min" in profile:
            line += (f"  range {profile['min']:g}–{profile['max']:g}  "
                     f"mean {profile['mean']}  "
                     f"outliers {profile['outliers']}")
        if profile.get("top_values"):
            top = ", ".join(f"{item['value']} ({item['count']})"
                            for item in profile["top_values"][:3])
            line += f"  top: {top}"
        lines.append(line)
    if report["issues"]:
        lines.append("")
        lines.append("Issues:")
        for issue in report["issues"]:
            where = f"[{issue['column']}] " if issue["column"] else ""
            lines.append(f"  {issue['severity'].upper():5} {where}"
                         f"{issue['code']}: {issue['message']}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check a CSV file for common data-quality problems.")
    parser.add_argument("csv_file", help="CSV file to check")
    parser.add_argument("--delimiter", default=None,
                        help="field delimiter (default: auto-detect)")
    parser.add_argument("--json", action="store_true",
                        help="print the report as JSON instead of text")
    parser.add_argument("--missing-threshold", type=float, default=0.2,
                        help="missing fraction above which a column warns "
                             "(default 0.2)")
    parser.add_argument("--fail-on", choices=["error", "warn"],
                        default="error",
                        help="exit non-zero on this severity and above "
                             "(default: error)")
    args = parser.parse_args(argv)

    try:
        report = check_csv(args.csv_file, delimiter=args.delimiter,
                           missing_threshold=args.missing_threshold)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"dqcheck: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_text(report))

    if report["verdict"] == "FAIL":
        return 2
    if report["verdict"] == "WARN" and args.fail_on == "warn":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
