"""Tests for Drift Watch. Run:  python -m unittest test_drift_watch -v
(or: python test_drift_watch.py)"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drift_watch as dw


class TestPSI(unittest.TestCase):
    def test_identical_distributions_score_near_zero(self):
        rng = np.random.default_rng(0)
        a = rng.normal(50, 10, 5000)
        b = rng.normal(50, 10, 5000)
        self.assertLess(dw.psi(a, b), 0.02)

    def test_strong_shift_scores_above_drift_threshold(self):
        rng = np.random.default_rng(1)
        a = rng.normal(50, 10, 5000)
        b = rng.normal(80, 10, 5000)
        self.assertGreater(dw.psi(a, b), 0.25)

    def test_small_shift_scores_in_watch_band(self):
        rng = np.random.default_rng(2)
        a = rng.normal(50, 10, 5000)
        b = rng.normal(54, 10, 5000)
        self.assertGreaterEqual(dw.psi(a, b), 0.05)
        self.assertLess(dw.psi(a, b), 0.25)


class TestKSTest(unittest.TestCase):
    def test_identical_distributions_high_pvalue(self):
        rng = np.random.default_rng(3)
        a = rng.normal(50, 10, 1000)
        b = rng.normal(50, 10, 1000)
        _, p = dw.ks_test(a, b)
        self.assertGreater(p, 0.05)

    def test_shifted_distributions_tiny_pvalue(self):
        rng = np.random.default_rng(4)
        a = rng.normal(50, 10, 1000)
        b = rng.normal(70, 10, 1000)
        _, p = dw.ks_test(a, b)
        self.assertLess(p, 0.001)


class TestSeverity(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(dw.severity(0.0), "STABLE")
        self.assertEqual(dw.severity(0.09), "STABLE")
        self.assertEqual(dw.severity(0.10), "WATCH")
        self.assertEqual(dw.severity(0.24), "WATCH")
        self.assertEqual(dw.severity(0.25), "DRIFT")
        self.assertEqual(dw.severity(1.5), "DRIFT")


class TestModel(unittest.TestCase):
    def test_logistic_regression_beats_majority_baseline(self):
        X, y = dw.generate_data(2000, seed=42)
        model = dw.train_logistic_regression(X, y)
        acc = dw.accuracy(model, X, y)
        majority = max(y.mean(), 1 - y.mean())
        # Default rate is low (~14%), so majority is a strong baseline;
        # accuracy alone barely beats it. The real check is ranking quality:
        # predicted probabilities must separate defaulters from non-defaulters.
        self.assertGreater(acc, majority)
        self.assertGreater(acc, 0.65)
        p = dw.predict_proba(model, X)
        pos = p[y == 1]
        neg = p[y == 0]
        # AUC via Mann-Whitney: P(score of a defaulter > score of a non-defaulter).
        # The synthetic labels are noisy by design, so the ceiling is ~0.77,
        # not 0.9+; the check is that the model clearly beats random (0.5).
        order = np.argsort(p)
        ranks = np.empty(len(p))
        ranks[order] = np.arange(1, len(p) + 1)
        n_pos, n_neg = int(y.sum()), int((1 - y).sum())
        auc = (ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
        self.assertGreater(auc, 0.70)
        self.assertGreater(pos.mean(), neg.mean() + 0.08)

    def test_age_is_irrelevant_to_the_true_rule(self):
        # The generating rule ignores age, so a model trained without age
        # should do about as well as one trained with it.
        X, y = dw.generate_data(3000, seed=42)
        full = dw.train_logistic_regression(X, y)
        no_age = dw.train_logistic_regression(np.delete(X, 1, axis=1), y)
        self.assertAlmostEqual(dw.accuracy(full, X, y),
                               dw.accuracy(no_age, np.delete(X, 1, axis=1), y),
                               delta=0.02)


class TestDemoEndToEnd(unittest.TestCase):
    def setUp(self):
        self.report = dw.run_demo()

    def test_overall_verdict_is_drift(self):
        self.assertEqual(self.report["overall_verdict"], "DRIFT")

    def test_drifted_features_flagged_and_control_stable(self):
        by_name = {f["feature"]: f for f in self.report["features"]}
        self.assertEqual(by_name["income"]["severity"], "DRIFT")
        self.assertEqual(by_name["credit_score"]["severity"], "DRIFT")
        self.assertEqual(by_name["loan_amount"]["severity"], "DRIFT")
        self.assertEqual(by_name["age"]["severity"], "STABLE")

    def test_prediction_distribution_drifted(self):
        self.assertGreater(self.report["prediction"]["psi"], 0.10)
        self.assertGreater(self.report["prediction"]["cur_mean_proba"],
                           self.report["prediction"]["ref_mean_proba"])

    def test_model_degrades_on_drifted_batch(self):
        m = self.report["model"]
        self.assertLess(m["current_accuracy"], m["train_accuracy"])

    def test_demo_is_deterministic(self):
        self.assertEqual(dw.run_demo(), self.report)

    def test_drift_drivers_listed(self):
        self.assertIn("income", self.report["drift_drivers"])
        self.assertNotIn("age", self.report["drift_drivers"])


class TestCLI(unittest.TestCase):
    def test_demo_cli_exits_1_on_drift_and_writes_json(self):
        here = os.path.dirname(os.path.abspath(__file__))
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "report.json")
            proc = subprocess.run(
                [sys.executable, os.path.join(here, "drift_watch.py"),
                 "--demo", "--out", out],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)  # DRIFT verdict
            self.assertIn("Overall verdict: DRIFT", proc.stdout)
            with open(out) as f:
                saved = json.load(f)
            self.assertEqual(saved["overall_verdict"], "DRIFT")

    def test_csv_mode_compares_features_only(self):
        rng = np.random.default_rng(5)
        ref = rng.normal(50, 10, (200, 2))
        cur = rng.normal(70, 10, (200, 2))
        with tempfile.TemporaryDirectory() as tmp:
            rp, cp = os.path.join(tmp, "ref.csv"), os.path.join(tmp, "cur.csv")
            for path, arr in ((rp, ref), (cp, cur)):
                with open(path, "w") as f:
                    f.write("a,b\n")
                    for row in arr:
                        f.write(f"{row[0]},{row[1]}\n")
            proc = subprocess.run(
                [sys.executable, os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "drift_watch.py"),
                 "--reference", rp, "--current", cp,
                 "--features", "a,b"],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("DRIFT", proc.stdout)
            self.assertNotIn("PREDICTION", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
