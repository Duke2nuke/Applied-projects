"""Tests for dqcheck. Run with: python -m unittest test_dqcheck -v"""

import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

import dqcheck

DIR = os.path.dirname(os.path.abspath(__file__))


def write_csv(rows, header):
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8")
    writer = csv.DictWriter(handle, fieldnames=header)
    writer.writeheader()
    writer.writerows(rows)
    handle.close()
    return handle.name


class TestCleanFile(unittest.TestCase):
    def test_clean_csv_passes(self):
        cities = ["Pune", "Mumbai", "Delhi"]
        path = write_csv(
            [{"id": str(i), "score": str(10 + i % 3), "city": cities[i % 3]}
             for i in range(12)],
            ["id", "score", "city"])
        try:
            report = dqcheck.check_csv(path)
        finally:
            os.unlink(path)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["error_count"], 0)
        self.assertEqual(report["warning_count"], 0)
        self.assertEqual(report["rows"], 12)


class TestMissingAndConstant(unittest.TestCase):
    def test_high_missing_warns(self):
        rows = [{"a": str(i), "b": "" if i < 4 else "x"} for i in range(12)]
        path = write_csv(rows, ["a", "b"])
        try:
            report = dqcheck.check_csv(path)
        finally:
            os.unlink(path)
        codes = {(i["column"], i["code"]) for i in report["issues"]}
        self.assertIn(("b", "high_missing"), codes)
        self.assertEqual(report["verdict"], "WARN")

    def test_constant_column_warns(self):
        rows = [{"a": str(i), "b": "same"} for i in range(12)]
        path = write_csv(rows, ["a", "b"])
        try:
            report = dqcheck.check_csv(path)
        finally:
            os.unlink(path)
        codes = {(i["column"], i["code"]) for i in report["issues"]}
        self.assertIn(("b", "constant_column"), codes)

    def test_empty_column_is_error(self):
        rows = [{"a": str(i), "b": ""} for i in range(5)]
        path = write_csv(rows, ["a", "b"])
        try:
            report = dqcheck.check_csv(path)
        finally:
            os.unlink(path)
        codes = {(i["column"], i["code"]) for i in report["issues"]}
        self.assertIn(("b", "empty_column"), codes)
        self.assertEqual(report["verdict"], "FAIL")


class TestDuplicatesAndTypes(unittest.TestCase):
    def test_duplicate_rows_counted(self):
        rows = [{"a": "1", "b": "x"}, {"a": "1", "b": "x"},
                {"a": "2", "b": "y"}]
        path = write_csv(rows, ["a", "b"])
        try:
            report = dqcheck.check_csv(path)
        finally:
            os.unlink(path)
        self.assertEqual(report["duplicate_rows"], 1)
        codes = {i["code"] for i in report["issues"]}
        self.assertIn("duplicate_rows", codes)

    def test_mixed_types_flagged(self):
        rows = [{"a": str(i), "b": "5" if i % 2 else "five"}
                for i in range(6)]
        path = write_csv(rows, ["a", "b"])
        try:
            report = dqcheck.check_csv(path)
        finally:
            os.unlink(path)
        codes = {(i["column"], i["code"]) for i in report["issues"]}
        self.assertIn(("b", "mixed_types"), codes)

    def test_numeric_profile(self):
        rows = [{"n": str(i)} for i in range(1, 11)]
        path = write_csv(rows, ["n"])
        try:
            report = dqcheck.check_csv(path)
        finally:
            os.unlink(path)
        profile = report["column_profiles"][0]
        self.assertEqual(profile["type"], "int")
        self.assertEqual(profile["min"], 1)
        self.assertEqual(profile["max"], 10)
        self.assertEqual(profile["mean"], 5.5)


class TestOutliersAndFormats(unittest.TestCase):
    def test_outlier_flagged(self):
        rows = [{"n": str(i)} for i in range(1, 12)]
        rows.append({"n": "500"})
        path = write_csv(rows, ["n"])
        try:
            report = dqcheck.check_csv(path)
        finally:
            os.unlink(path)
        codes = {(i["column"], i["code"]) for i in report["issues"]}
        self.assertIn(("n", "outliers"), codes)

    def test_invalid_email_flagged(self):
        rows = [{"email": "ok@example.com" if i else "not-an-email"}
                for i in range(5)]
        path = write_csv(rows, ["email"])
        try:
            report = dqcheck.check_csv(path)
        finally:
            os.unlink(path)
        codes = {(i["column"], i["code"]) for i in report["issues"]}
        self.assertIn(("email", "invalid_email"), codes)

    def test_bad_date_flagged(self):
        rows = [{"signup_date": "2026-01-0" + str(i)} for i in range(1, 5)]
        rows.append({"signup_date": "yesterday"})
        path = write_csv(rows, ["signup_date"])
        try:
            report = dqcheck.check_csv(path)
        finally:
            os.unlink(path)
        codes = {(i["column"], i["code"]) for i in report["issues"]}
        self.assertIn(("signup_date", "bad_date"), codes)


class TestCli(unittest.TestCase):
    def test_example_csv_fails_with_real_counts(self):
        result = subprocess.run(
            [sys.executable, os.path.join(DIR, "dqcheck.py"),
             os.path.join(DIR, "example.csv")],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)  # FAIL: errors present
        self.assertIn("Verdict: FAIL", result.stdout)

    def test_json_output_parses(self):
        result = subprocess.run(
            [sys.executable, os.path.join(DIR, "dqcheck.py"),
             os.path.join(DIR, "example.csv"), "--json"],
            capture_output=True, text=True)
        report = json.loads(result.stdout)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual(report["rows"], 12)
        self.assertEqual(report["duplicate_rows"], 1)

    def test_fail_on_warn_exit_code(self):
        rows = [{"a": str(i), "b": "" if i < 4 else "x"} for i in range(12)]
        path = write_csv(rows, ["a", "b"])
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(DIR, "dqcheck.py"), path,
                 "--fail-on", "warn"],
                capture_output=True, text=True)
        finally:
            os.unlink(path)
        self.assertEqual(result.returncode, 1)

    def test_missing_file_exits_2(self):
        result = subprocess.run(
            [sys.executable, os.path.join(DIR, "dqcheck.py"), "nope.csv"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
