"""Tests for Fraud-Guard. Run:  python -m unittest test_fraud_guard -v"""

import unittest

import numpy as np

from fraud_guard import (FRAUD_RATE, TARGET_RECALL, build_models, evaluate,
                         generate_data, run_pipeline, split_data,
                         tune_threshold)


class TestData(unittest.TestCase):
    def test_shape_and_imbalance(self):
        X, y = generate_data()
        self.assertEqual(X.shape, (10_000, 20))
        self.assertEqual(len(y), 10_000)
        # ~3% fraud, allow sampling noise of +/-1 percentage point
        self.assertAlmostEqual(float(np.mean(y)), FRAUD_RATE, delta=0.01)
        self.assertSetEqual(set(np.unique(y)), {0, 1})

    def test_split_is_stratified(self):
        X, y = generate_data()
        _, _, _, y_test = split_data(X, y)
        self.assertAlmostEqual(float(np.mean(y_test)), FRAUD_RATE, delta=0.01)

    def test_reproducible(self):
        X1, y1 = generate_data()
        X2, y2 = generate_data()
        np.testing.assert_array_equal(X1, X2)
        np.testing.assert_array_equal(y1, y2)


class TestThresholdTuning(unittest.TestCase):
    def test_tuning_hits_target_recall(self):
        y = np.array([0, 0, 0, 0, 1, 1, 0, 1, 0, 0])
        proba = np.array([0.1, 0.2, 0.3, 0.4, 0.9, 0.8, 0.15, 0.7, 0.05, 0.25])
        tuned = tune_threshold(y, proba, target_recall=0.8)
        # 3 positives; recall 0.8 needs >= 2.4 -> 3 caught at threshold 0.7
        self.assertGreaterEqual(tuned["recall"], 0.8)
        self.assertAlmostEqual(tuned["threshold"], 0.7)

    def test_tuning_meets_target_and_moves_threshold_correctly(self):
        X, y = generate_data()
        X_train, X_test, y_train, y_test = split_data(X, y)
        model = build_models()["logistic_regression"]
        model.fit(X_train, y_train)
        m = evaluate(model, X_test, y_test)
        # Tuned threshold always lands recall at (just above) the target.
        self.assertGreaterEqual(m["recall@tuned"], TARGET_RECALL)
        self.assertLess(m["recall@tuned"], TARGET_RECALL + 0.05)
        # If default recall already beats the target, tuning RAISES the
        # threshold (recall falls to the target, precision rises).
        # If default recall is below it, tuning LOWERS the threshold.
        if m["recall@0.5"] >= TARGET_RECALL:
            self.assertGreaterEqual(m["tuned_threshold"], 0.5)
            self.assertGreaterEqual(m["precision@tuned"], m["precision@0.5"])
        else:
            self.assertLess(m["tuned_threshold"], 0.5)
            self.assertGreaterEqual(m["recall@tuned"], m["recall@0.5"])


class TestPipeline(unittest.TestCase):
    def test_models_train_and_metrics_are_sane(self):
        results = run_pipeline()
        self.assertTrue(results["dataset"]["synthetic"])
        for name in ("logistic_regression", "random_forest"):
            m = results[name]
            for key in ("accuracy", "precision@0.5", "recall@0.5", "f1@0.5",
                        "roc_auc", "pr_auc", "precision@tuned", "recall@tuned"):
                self.assertGreaterEqual(m[key], 0.0, f"{name}.{key}")
                self.assertLessEqual(m[key], 1.0, f"{name}.{key}")
            # Both models must beat the "predict everything legit" baseline
            # on PR-AUC (baseline = fraud rate ~0.03) by a wide margin.
            self.assertGreater(m["pr_auc"], 0.20)
            # Tuned threshold must reach the target recall.
            self.assertGreaterEqual(m["recall@tuned"], TARGET_RECALL)
            # Confusion counts must add up to the test size.
            c = m["confusion@0.5"]
            self.assertEqual(sum(c.values()), results["dataset"]["test_size"])


if __name__ == "__main__":
    unittest.main()
