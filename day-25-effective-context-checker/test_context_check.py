"""Tests for the effective-context checker (stdlib unittest)."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import context_check as cc

HERE = Path(__file__).parent


class TestTokenEstimate(unittest.TestCase):
    def test_empty(self):
        est, _, _ = cc.estimate_tokens("")
        self.assertEqual(est, 0)

    def test_known_text(self):
        # 400 chars -> chars/4 = 100; ~80 words * 1.33 = ~106 -> max ~106
        text = ("word " * 80).strip()
        est, by_chars, by_words = cc.estimate_tokens(text)
        self.assertEqual(by_chars, len(text) / 4)
        self.assertAlmostEqual(by_words, 80 * 1.33, places=1)
        self.assertEqual(est, max(by_chars, by_words))


class TestVerdict(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(cc.verdict(1000, 128000, 64000), "OK")

    def test_warning_past_effective(self):
        self.assertEqual(cc.verdict(70000, 128000, 64000), "WARNING")

    def test_over_advertised(self):
        self.assertEqual(cc.verdict(200000, 128000, 64000), "OVER")

    def test_boundary_effective_is_ok(self):
        self.assertEqual(cc.verdict(64000, 128000, 64000), "OK")


class TestCheckPrompt(unittest.TestCase):
    def setUp(self):
        self.models = cc.load_models()

    def test_cost_math(self):
        model = self.models["claude-sonnet-4.5"]  # $3.00 / 1M
        text = "x" * 400400  # ~100,100 tokens by chars/4, just past effective
        result = cc.check_prompt(text, model)
        self.assertAlmostEqual(result["cost_per_call_usd"], 0.30, places=2)
        self.assertEqual(result["verdict"], "WARNING")  # 100,100 > 100,000 effective

    def test_overrides(self):
        model = self.models["gpt-4o-mini"]
        text = "hello world " * 10000  # ~33k tokens
        result = cc.check_prompt(text, model, effective_override=1000)
        self.assertEqual(result["verdict"], "WARNING")
        self.assertEqual(result["effective_tokens"], 1000)


class TestModelsTable(unittest.TestCase):
    def test_all_models_sane(self):
        models = cc.load_models()
        self.assertGreaterEqual(len(models), 3)
        for m in models.values():
            self.assertGreater(m["advertised_tokens"], m["effective_tokens"])
            self.assertGreater(m["effective_tokens"], 0)
            self.assertGreater(m["input_price_per_1m_usd"], 0)


class TestNeedleEval(unittest.TestCase):
    def test_deterministic_same_seed(self):
        a = cc.needle_eval(sizes=(500, 1000), trials=2, seed=7)
        b = cc.needle_eval(sizes=(500, 1000), trials=2, seed=7)
        self.assertEqual(a, b)

    def test_rows_shape(self):
        rows = cc.needle_eval(sizes=(500,), trials=2, seed=7)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target_tokens"], 500)
        self.assertTrue(0 <= rows[0]["hit_at_1"] <= 1)
        self.assertTrue(rows[0]["hit_at_3"] >= rows[0]["hit_at_1"])

    def test_needle_in_exactly_one_chunk(self):
        ctx = cc.build_context(1000, seed=3)
        chunks = cc._chunk_words(ctx.split())
        hits = [i for i, c in enumerate(chunks) if "84712" in c]
        self.assertEqual(len(hits), 1)


class TestCLI(unittest.TestCase):
    def test_check_example_file(self):
        r = subprocess.run(
            [sys.executable, "context_check.py", "check",
             "--model", "gpt-4o-mini",
             "--file", "examples/sample-prompt.txt"],
            cwd=HERE, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Verdict: OK", r.stdout)
        self.assertIn("Tokens (est.)", r.stdout)

    def test_unknown_model_fails(self):
        r = subprocess.run(
            [sys.executable, "context_check.py", "check",
             "--model", "not-a-model",
             "--file", "examples/sample-prompt.txt"],
            cwd=HERE, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("Unknown model", r.stderr)

    def test_models_lists(self):
        r = subprocess.run(
            [sys.executable, "context_check.py", "models"],
            cwd=HERE, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("gpt-4o-mini", r.stdout)


if __name__ == "__main__":
    unittest.main()
