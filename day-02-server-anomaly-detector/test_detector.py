"""Tests for the detector. Run: python -m unittest test_detector -v"""

import unittest

import numpy as np
import pandas as pd

from detector import FEATURES, detect, evaluate, modified_z_scores


def _frame(values_by_feature, n=60):
    data = {"timestamp": pd.date_range("2026-10-01", periods=n, freq="h")}
    for feature in FEATURES:
        data[feature] = values_by_feature.get(feature, np.full(n, 50.0))
    data["is_anomaly"] = False
    return pd.DataFrame(data)


class TestDetector(unittest.TestCase):
    def test_obvious_spike_is_flagged(self):
        values = np.full(100, 50.0)
        values[90] = 99.0  # after the 72-point warm-up window
        df = _frame({"cpu_percent": values}, n=100)
        result = detect(df)
        self.assertTrue(result.loc[90, "predicted_anomaly"])

    def test_flat_series_has_no_false_positives(self):
        result = detect(_frame({}))
        self.assertFalse(result["predicted_anomaly"].any())

    def test_warmup_window_is_never_flagged(self):
        values = np.full(60, 50.0)
        values[5] = 99.0  # inside the 48-point warm-up window
        result = detect(_frame({"cpu_percent": values}))
        self.assertFalse(result.loc[5, "predicted_anomaly"])

    def test_evaluate_counts_are_consistent(self):
        df = _frame({})
        df.loc[40, "is_anomaly"] = True
        result = detect(df)
        metrics = evaluate(result)
        self.assertEqual(
            metrics["true_positives"] + metrics["false_negatives"], 1
        )


if __name__ == "__main__":
    unittest.main()
