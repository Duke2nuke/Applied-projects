# LOCAL EDUCATIONAL LAB — own code only, never run against real systems
"""Tests for the lab project (LAB ONLY).

LOCAL EDUCATIONAL LAB — own code only, never run against real systems.
Localhost / local files only. No network, no external systems.
Run:  python test_lab.py
"""
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import audit  # noqa: E402
import fixed_app  # noqa: E402


class TestScanner(unittest.TestCase):
    def test_scanner_finds_all_three_flaws_in_vulnerable_code(self):
        findings = audit.scan_file(BASE_DIR / "app.py")
        types = sorted(f["type"] for f in findings)
        self.assertEqual(len(findings), 3, f"expected 3 flaws, got {findings}")
        self.assertEqual(
            types,
            sorted(
                [
                    audit.SQL_INJECTION,
                    audit.REFLECTED_XSS,
                    audit.PLAINTEXT_PASSWORD,
                ]
            ),
        )

    def test_scanner_finds_zero_flaws_in_fixed_code(self):
        findings = audit.scan_file(BASE_DIR / "fixed_app.py")
        self.assertEqual(findings, [], f"expected 0 flaws, got {findings}")


class TestFixedLogin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test_fixed.db"
        fixed_app.DB_PATH = self.db_path
        fixed_app.init_db(self.db_path)
        self.client = fixed_app.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_fixed_login_works_with_hashed_password(self):
        # Stored value is a salted hash, never the demo plaintext.
        row = fixed_app.get_user("demo")
        self.assertIsNotNone(row)
        self.assertNotEqual(row[1], "password123")
        self.assertIn(":", row[1])
        self.assertTrue(fixed_app.verify_password("password123", row[1]))
        self.assertFalse(fixed_app.verify_password("wrong-password", row[1]))
        # End-to-end over the local test client (no network).
        ok = self.client.post(
            "/login", data={"username": "demo", "password": "password123"}
        )
        self.assertEqual(ok.status_code, 200)
        self.assertIn("Logged in as demo", ok.get_data(as_text=True))
        bad = self.client.post(
            "/login", data={"username": "demo", "password": "wrong-password"}
        )
        self.assertEqual(bad.status_code, 401)

    def test_fixed_greet_escapes_user_input(self):
        resp = self.client.get("/greet", query_string={"name": "<script>alert(1)</script>"})
        body = resp.get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", body)
        self.assertIn("&lt;script&gt;", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
