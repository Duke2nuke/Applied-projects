# Day 11 — Daily Demand Forecaster (Day B: AI/ML Python)

A stdlib-only Python time-series forecaster: given a year of daily
demand (synthetic campus-canteen orders), predict tomorrow's orders.
It compares three models under honest walk-forward evaluation and
prints a 7-day forecast.

This is deliberately not a repeat of earlier days: Day 02 did
anomaly detection on server metrics, Day 05 clustered customers,
Day 08 did tabular regression on house prices, and Day 10 retrieved
documents. This one is the missing ML type so far — **forecasting a
series over time**, where the order of the data matters and a random
train/test split would leak the future.

## How to run

No dependencies — Python 3.10+ standard library only.

```bash
python run.py            # full report + 7-day forecast
python run.py --days 14  # longer horizon
python -m unittest test_forecast -v
```

## Example output (actually run, 6 Nov 2026)

```
Daily demand forecaster — 365 synthetic days (campus canteen orders)
Series range: 74.0 to 198.5 orders/day, mean 139.6

Walk-forward evaluation (train on first 200 days,
one-step-ahead on the last 165):
model           MAE     RMSE
naive         18.23    23.43
seasonal       9.07    11.17
ridge          7.60     9.38

Best by MAE: ridge (7.60 vs seasonal-naive 9.07)

Next 7-day forecast (ridge, feeding predictions back in):
  day +1:  182.7 orders
  day +2:  183.8 orders
  day +3:  178.2 orders
  day +4:  171.7 orders
  day +5:  133.4 orders
  day +6:  135.1 orders
  day +7:  182.2 orders
```

The weekend dip in the forecast (days +5/+6) is the model recovering
the planted weekly seasonality — weekends run ~28 orders lower.

## How it works

- **Data** (`forecast.py`, `generate_series`): 365 synthetic days —
  base 120 orders + 0.15/day trend + a weekly cycle (weekend dip,
  sine term) + Gaussian noise (σ=8). Seeded, so every run reproduces
  the same series. Clearly labelled synthetic; no real canteen data.
- **Features**: lags 1, 7 and 14 days, a trend index, and a
  day-of-week one-hot. Only past data is ever used for a forecast —
  the tests check this explicitly.
- **Models**: naive (tomorrow = today), seasonal-naive (tomorrow =
  same weekday last week), and ridge regression solved in closed form
  (normal equations + Gaussian elimination; intercept unpenalised).
- **Evaluation**: expanding-window walk-forward — train on the first
  200 days, predict one day ahead, roll forward, refit every 30 days.
  A random split would leak the future, so it is not used.

## Results

| model | MAE | RMSE |
|---|---|---|
| naive | 18.23 | 23.43 |
| seasonal-naive | 9.07 | 11.17 |
| ridge | **7.60** | **9.38** |

Weekly seasonality does most of the work (naive → seasonal-naive
halves the error); the ridge model adds lags and trend to shave a
further ~16% off the MAE. The residual error is close to the injected
noise (σ=8), so the model is near the ceiling this synthetic series
allows.

Tests: 7/7 pass — determinism, weekend dip, past-only features,
seasonal beats naive, ridge beats seasonal, sane forecast range.

## Limits

- Synthetic data with a known, stable generating process — real
  demand has holidays, exams, weather, and regime changes this
  series does not.
- Ridge is linear; it cannot learn interactions (e.g. trend ×
  weekday) or sudden level shifts.
- Multi-day forecasts feed predictions back in, so error compounds
  with horizon — day +7 is less trustworthy than day +1.

## 2-minute explainer

**Problem:** a canteen (or any small business) wants to know how much
to prep tomorrow — over-prep wastes food, under-prep loses sales.
**Approach:** I generated a year of synthetic daily orders with a
trend and a weekly cycle, then compared three forecasters under
walk-forward evaluation, which is the honest way to test a time
series — you only ever predict the next day from the past, then roll
forward. The ridge model uses the last 1, 7 and 14 days, the trend,
and the day of the week. **Results:** it beats the seasonal-naive
baseline, 7.6 vs 9.1 mean absolute error, on data whose noise floor
is about 8 — so it is close to as good as this series allows, and it
recovers the weekend dip on its own. **Limits:** the data is
synthetic and stable; real demand has holidays and shocks, and the
model is linear, so it would miss those.
