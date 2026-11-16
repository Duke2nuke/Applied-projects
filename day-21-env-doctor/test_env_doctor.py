"""Tests for env_doctor.py — run with: python -m unittest test_env_doctor -v"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import env_doctor


def _write(tmp, name, text):
    p = Path(tmp) / name
    p.write_text(text)
    return str(p)


class TestParsing(unittest.TestCase):
    def test_basic_key_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _write(tmp, ".env", "DATABASE_URL=postgres://localhost/db\nPORT=8000\n")
            env = env_doctor.EnvFile(p)
            self.assertEqual(env.values["DATABASE_URL"], "postgres://localhost/db")
            self.assertEqual(env.values["PORT"], "8000")

    def test_export_prefix_quotes_and_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = ('# a comment\n'
                    'export API_KEY="sk-live-123"\n'
                    "SECRET='a#b c'\n"
                    'DEBUG=true # enable debug\n'
                    'EMPTY=\n')
            p = _write(tmp, ".env", text)
            env = env_doctor.EnvFile(p)
            self.assertEqual(env.values["API_KEY"], "sk-live-123")
            self.assertEqual(env.values["SECRET"], "a#b c")
            self.assertEqual(env.values["DEBUG"], "true")
            self.assertEqual(env.values["EMPTY"], "")

    def test_duplicate_key_records_all_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _write(tmp, ".env", "PORT=8000\nPORT=9000\n")
            env = env_doctor.EnvFile(p)
            self.assertEqual(env.values["PORT"], "9000")  # last wins
            self.assertEqual(env.duplicates["PORT"], [1, 2])

    def test_malformed_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _write(tmp, ".env", "GOOD=1\nno equals here\n1BAD=2\n")
            env = env_doctor.EnvFile(p)
            self.assertEqual(env.values, {"GOOD": "1"})
            self.assertEqual([m[0] for m in env.malformed], [2, 3])

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            env_doctor.EnvFile("/nonexistent/.env")


class TestAudit(unittest.TestCase):
    def _pair(self, tmp, env_text, ex_text):
        env = _write(tmp, ".env", env_text)
        ex = _write(tmp, ".env.example", ex_text)
        return env, ex

    def test_clean_pair_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            env, ex = self._pair(tmp, "A=1\nB=2\n", "A=\nB=\n")
            report = env_doctor.audit(env, ex)
            self.assertFalse(env_doctor.audit_problems(report))
            self.assertEqual(report["missing"], [])
            self.assertEqual(report["extra"], [])

    def test_missing_extra_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            env, ex = self._pair(tmp,
                                 "A=1\nB=\nSTALE=x\n",
                                 "A=\nB=\nC=\n")
            report = env_doctor.audit(env, ex)
            self.assertEqual(report["missing"], ["C"])
            self.assertEqual(report["extra"], ["STALE"])
            self.assertEqual(report["empty"], ["B"])
            self.assertTrue(env_doctor.audit_problems(report))
            # extra alone is a warning, not a failure
            self.assertFalse(env_doctor.audit_problems(
                {**report, "missing": [], "empty": [], "duplicates": {},
                 "malformed": [], "example_malformed": []}))
            self.assertTrue(env_doctor.audit_problems(
                {**report, "missing": [], "empty": [], "duplicates": {},
                 "malformed": [], "example_malformed": []}, strict=True))


class TestInitAndFix(unittest.TestCase):
    def test_init_redacts_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = _write(tmp, ".env", "API_KEY=sk-secret\nPORT=8000\n")
            ex = str(Path(tmp) / ".env.example")
            keys = env_doctor.init_example(env, ex)
            self.assertEqual(keys, ["API_KEY", "PORT"])
            text = Path(ex).read_text()
            self.assertNotIn("sk-secret", text)
            self.assertIn("API_KEY=", text)
            self.assertIn("PORT=", text)

    def test_init_refuses_to_overwrite_foreign_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = _write(tmp, ".env", "A=1\n")
            ex = _write(tmp, ".env.example", "A=\n")
            with self.assertRaises(FileExistsError):
                env_doctor.init_example(env, ex)

    def test_fix_appends_missing_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = _write(tmp, ".env", "A=1\n")
            ex = _write(tmp, ".env.example", "A=\nB=\nC=\n")
            added = env_doctor.fix_env(env, ex)
            self.assertEqual(added, ["B", "C"])
            after = env_doctor.EnvFile(env)
            self.assertEqual(sorted(after.values), ["A", "B", "C"])
            self.assertEqual(env_doctor.audit(env, ex)["missing"], [])


class TestCLI(unittest.TestCase):
    def test_cli_audit_exit_codes_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, ".env", "A=1\n")
            _write(tmp, ".env.example", "A=\nB=\n")
            proc = subprocess.run(
                [sys.executable, "env_doctor.py", "audit",
                 "--env", str(Path(tmp) / ".env"),
                 "--example", str(Path(tmp) / ".env.example")],
                capture_output=True, text=True, cwd=Path(__file__).parent)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("MISSING", proc.stdout)
            self.assertIn("B", proc.stdout)

            proc = subprocess.run(
                [sys.executable, "env_doctor.py", "audit", "--json",
                 "--env", str(Path(tmp) / ".env"),
                 "--example", str(Path(tmp) / ".env.example")],
                capture_output=True, text=True, cwd=Path(__file__).parent)
            report = json.loads(proc.stdout)
            self.assertEqual(report["missing"], ["B"])


if __name__ == "__main__":
    unittest.main()
