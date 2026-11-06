"""Tests for the daily demand forecaster. Run with:

    python -m unittest test_forecast -v
"""

import unittest

from forecast import (
    fit_ridge,
    forecast_next_days,
    generate_series,
    make_features,
    naive_forecast,
    ridge_forecast,
    seasonal_naive_forecast,
    walk_forward,
)


class TestData(unittest.TestCase):
    def test_series_is_deterministic(self):
        self.assertEqual(generate_series(), generate_series())

    def test_series_length_and_weekend_dip(self):
        s = generate_series()
        self.assertEqual(len(s), 365)
        weekdays = [s[t] for t in range(365) if t % 7 < 5]
        weekends = [s[t] for t in range(365) if t % 7 >= 5]
        self.assertLess(sum(weekends) / len(weekends),
                        sum(weekdays) / len(weekdays))

    def test_features_use_only_past(self):
        s = generate_series()
        f = make_features(s, 20)
        self.assertEqual(len(f), 11)          # 1 + 3 lags + trend + 6 dow
        self.assertEqual(f[1], s[19])         # lag 1
        self.assertEqual(f[2], s[13])         # lag 7
        self.assertEqual(f[3], s[6])          # lag 14


class TestModels(unittest.TestCase):
    def test_seasonal_beats_naive_on_seasonal_data(self):
        s = generate_series()
        r = walk_forward(s)
        self.assertLess(r["seasonal"][0], r["naive"][0])

    def test_ridge_beats_seasonal_naive(self):
        s = generate_series()
        r = walk_forward(s)
        self.assertLess(r["ridge"][0], r["seasonal"][0])

    def test_ridge_forecast_is_finite_and_sane(self):
        s = generate_series()
        w = fit_ridge(s, len(s))
        pred = ridge_forecast(s, w, len(s))
        self.assertTrue(50.0 < pred < 300.0)

    def test_forecast_next_days_length(self):
        s = generate_series()
        preds = forecast_next_days(s, horizon=7)
        self.assertEqual(len(preds), 7)
        self.assertTrue(all(50.0 < p < 300.0 for p in preds))


if __name__ == "__main__":
    unittest.main()
