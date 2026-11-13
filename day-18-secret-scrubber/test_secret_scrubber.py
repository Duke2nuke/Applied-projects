"""Tests for secret_scrubber.py.

All "secrets" in this file are FAKE, hand-made example values used only
to prove the redaction patterns work. None of them is a real credential:
the AWS key is the documented example key AKIAIOSFODNN7EXAMPLE, the
tokens are invented strings, and the JWT payload says "fake-user".
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from secret_scrubber import scrub_text  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "secret_scrubber.py")


class TestPatterns(unittest.TestCase):
    def test_aws_access_key(self):
        out = scrub_text("key is AKIAIOSFODNN7EXAMPLE here")
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", out.text)
        self.assertIn("[REDACTED:AWS_ACCESS_KEY]", out.text)
        self.assertEqual(out.counts["AWS_ACCESS_KEY"], 1)

    def test_github_token(self):
        fake = "ghp_" + "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx2"
        out = scrub_text(f"token={fake}")
        self.assertNotIn(fake, out.text)
        self.assertEqual(out.counts["GITHUB_TOKEN"], 1)

    def test_slack_token(self):
        out = scrub_text("slack: xoxb-123456789012-FAKE-abcdef")
        self.assertNotIn("xoxb-123456789012", out.text)
        self.assertEqual(out.counts["SLACK_TOKEN"], 1)

    def test_jwt(self):
        fake_jwt = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
                    ".eyJzdWIiOiJmYWtlLXVzZXIifQ"
                    ".FakeSignatureForTestingOnly1234567890")
        out = scrub_text(f"Authorization: Bearer {fake_jwt}")
        self.assertNotIn("eyJhbGciOi", out.text)
        self.assertEqual(out.counts["JWT"], 1)

    def test_bearer_token_keeps_scheme(self):
        out = scrub_text("Authorization: Bearer abcdefghij1234567890XYZ")
        self.assertIn("Bearer [REDACTED:BEARER_TOKEN]", out.text)
        self.assertEqual(out.counts["BEARER_TOKEN"], 1)

    def test_url_password_keeps_user_and_host(self):
        out = scrub_text("db at postgres://appuser:s3cretPass9@db.internal:5432/app")
        self.assertIn("postgres://appuser:[REDACTED:URL_PASSWORD]@db.internal:5432/app",
                      out.text)
        self.assertNotIn("s3cretPass9", out.text)

    def test_generic_api_key_assignment_keeps_key_name(self):
        out = scrub_text('api_key = "sk-fake-key-for-testing-123456"')
        self.assertEqual(out.text,
                         'api_key = "[REDACTED:GENERIC_SECRET]"')
        self.assertNotIn("sk-fake-key-for-testing", out.text)
        self.assertEqual(out.counts["GENERIC_SECRET"], 1)

    def test_private_key_block(self):
        key_block = ("-----BEGIN RSA PRIVATE KEY-----\n"
                     "MIIFakeKeyMaterialForTestingOnly\n"
                     "-----END RSA PRIVATE KEY-----")
        out = scrub_text("leaked:\n" + key_block)
        self.assertNotIn("MIIFakeKeyMaterial", out.text)
        self.assertNotIn("BEGIN RSA PRIVATE KEY", out.text)
        self.assertEqual(out.counts["PRIVATE_KEY_BLOCK"], 1)

    def test_placeholders_are_not_redacted(self):
        text = 'api_key = "your-key-here"\npassword = "***"\ntoken = "${API_TOKEN}"'
        out = scrub_text(text)
        self.assertEqual(out.text, text)
        self.assertEqual(out.total, 0)

    def test_clean_text_untouched(self):
        text = "2026-11-13 INFO server started on port 8080\nno secrets here\n"
        out = scrub_text(text)
        self.assertEqual(out.text, text)
        self.assertEqual(out.total, 0)
        self.assertEqual(out.lines_changed, 0)

    def test_email_opt_in(self):
        out = scrub_text("contact demo@example.com", include_email=True)
        self.assertIn("[REDACTED:EMAIL]", out.text)
        out2 = scrub_text("contact demo@example.com")
        self.assertIn("demo@example.com", out2.text)  # off by default

    def test_credit_card_luhn_validated(self):
        # 4242 4242 4242 4242 is the standard test card number (Luhn-valid).
        out = scrub_text("card 4242424242424242 charged", include_cards=True)
        self.assertIn("[REDACTED:CREDIT_CARD]", out.text)
        # 1234 5678 9012 3456 fails Luhn — must NOT be redacted as a card.
        out2 = scrub_text("ref 1234567890123456 filed", include_cards=True)
        self.assertIn("1234567890123456", out2.text)
        self.assertEqual(out2.total, 0)

    def test_scrubbing_is_idempotent(self):
        text = ("AKIAIOSFODNN7EXAMPLE\n"
                "postgres://appuser:s3cretPass9@db.internal:5432/app\n"
                'api_key = "sk-fake-key-for-testing-123456"\n')
        once = scrub_text(text)
        twice = scrub_text(once.text)
        self.assertEqual(twice.text, once.text)
        self.assertEqual(twice.total, 0)

    def test_report_counts_without_secret_values(self):
        out = scrub_text("AKIAIOSFODNN7EXAMPLE and AKIAIOSFODNN7EXAMPLE")
        self.assertEqual(out.counts["AWS_ACCESS_KEY"], 2)
        self.assertEqual(out.total, 2)
        self.assertEqual(out.lines_scanned, 1)
        self.assertEqual(out.lines_changed, 1)


class TestCLI(unittest.TestCase):
    def run_cli(self, args, stdin_text=None):
        return subprocess.run([sys.executable, SCRIPT] + args,
                              input=stdin_text, capture_output=True,
                              text=True)

    def test_stdin_stdout(self):
        res = self.run_cli([], stdin_text="key AKIAIOSFODNN7EXAMPLE\n")
        self.assertEqual(res.returncode, 0)
        self.assertIn("[REDACTED:AWS_ACCESS_KEY]", res.stdout)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", res.stdout)

    def test_check_mode_exit_codes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".log",
                                         delete=False) as fh:
            fh.write("clean log line\n")
            clean = fh.name
        with tempfile.NamedTemporaryFile("w", suffix=".log",
                                         delete=False) as fh:
            fh.write("leaked AKIAIOSFODNN7EXAMPLE\n")
            dirty = fh.name
        try:
            self.assertEqual(self.run_cli(["--check", clean]).returncode, 0)
            dirty_res = self.run_cli(["--check", dirty])
            self.assertEqual(dirty_res.returncode, 1)
            self.assertIn("AWS_ACCESS_KEY", dirty_res.stderr)
        finally:
            os.unlink(clean)
            os.unlink(dirty)

    def test_in_place_keeps_backup(self):
        with tempfile.NamedTemporaryFile("w", suffix=".log",
                                         delete=False) as fh:
            fh.write("token ghp_" + "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx2\n")
            path = fh.name
        try:
            res = self.run_cli(["--in-place", path])
            self.assertEqual(res.returncode, 0)
            with open(path) as fh:
                self.assertIn("[REDACTED:GITHUB_TOKEN]", fh.read())
            with open(path + ".bak") as fh:
                self.assertIn("ghp_Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx2",
                              fh.read())
        finally:
            os.unlink(path)
            os.unlink(path + ".bak")

    def test_report_json_has_counts_not_values(self):
        with tempfile.NamedTemporaryFile("w", suffix=".log",
                                         delete=False) as fh:
            fh.write("AKIAIOSFODNN7EXAMPLE\n")
            path = fh.name
        report = path + ".report.json"
        try:
            res = self.run_cli(["--report", report, path])
            self.assertEqual(res.returncode, 0)
            with open(report) as fh:
                data = json.load(fh)
            self.assertEqual(data["total_redactions"], 1)
            self.assertEqual(data["by_type"]["AWS_ACCESS_KEY"], 1)
            self.assertNotIn("AKIAIOSFODNN7EXAMPLE",
                             json.dumps(data))
        finally:
            os.unlink(path)
            if os.path.exists(report):
                os.unlink(report)

    def test_custom_pattern_via_config(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as fh:
            json.dump({"patterns": [
                {"name": "INTERNAL_ID",
                 "regex": r"\bINT-[0-9]{6}\b"}]}, fh)
            cfg = fh.name
        try:
            res = self.run_cli(["--config", cfg], stdin_text="id INT-123456\n")
            self.assertIn("[REDACTED:INTERNAL_ID]", res.stdout)
        finally:
            os.unlink(cfg)


if __name__ == "__main__":
    unittest.main()
