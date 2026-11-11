# sktime Time-Series Forecaster — Proof Project

A small, honest proof that Aarambh can use the **sktime** library itself:
three sktime forecasters fitted and evaluated on a real time series, with a
naive baseline for comparison.

**Not affiliated with sktime. Not a sktime contribution, not submitted
anywhere. Local build only — nothing here has been pushed, posted, or
shown to sktime.**

## Dataset

`sktime.datasets.load_airline()` — the classic AirPassengers series:
monthly international airline passengers, Jan 1949 – Dec 1960,
**144 observations**, all positive, no missing values.
Source: Box & Jenkins, as shipped with sktime.

## Method

- Train/test split: first **120 months** train (1949-01 – 1958-12),
  last **24 months** test (1959-01 – 1960-12). No shuffling — a
  temporal split, as forecasting requires.
- Metrics: MAE and RMSE from `sktime.performance_metrics.forecasting`,
  on the 24-month held-out period.
- Seasonal period: 12 (monthly data).

## Models (all sktime forecasters)

| Model | sktime class | MAE | RMSE | vs seasonal naive |
|---|---|---:|---:|---:|
| Seasonal naive (baseline) | `NaiveForecaster(strategy="last", sp=12)` | 71.25 | 76.99 | — |
| ETS (additive trend + seasonal) | `ExponentialSmoothing(trend="add", seasonal="add", sp=12)` | **31.08** | **35.76** | **56.4% better** |
| Random forest reduction | `make_reduction(RandomForestRegressor(n_estimators=200), window_length=12)` | 47.07 | 59.84 | 33.9% better |

Best by MAE: **ETS, 31.08**.

## Honest notes

- `AutoETS` (sktime's automatic ETS selection) was tried first and was
  **worse than the seasonal-naive baseline** (MAE 115.25), so it was
  dropped in favour of the explicitly specified additive ETS(A,A,A).
  That failure is recorded here rather than hidden.
- A SARIMA(1,1,1)(1,1,1,12) was also tried during development
  (MAE 68.04, about the same as naive) and not kept.
- This is one small, well-known series. It proves the author can load
  data, fit sktime forecasters, and evaluate them properly — it is not
  production forecasting and says nothing about other datasets.

## Reproduce

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python src/forecast.py        # prints metrics, writes results.json
.venv/bin/python -m pytest tests/ -v   # 4 tests
```

Environment used: Python 3.12, sktime 1.3.0, scikit-learn 1.9.1,
statsmodels (for ETS), pytest 9.2.0.

## Files

- `src/forecast.py` — data loading, the three forecasters, evaluation
- `tests/test_forecaster.py` — 4 tests (data, fit/predict, metrics, run)
- `results.json` — exact metrics from the last run
- `requirements.txt` — sktime, statsmodels, pytest

## What is still missing to show it to sktime

- A real sktime issue to attach it to — the newest sktime
  good-first-issues checked 11 Nov 2026 were all already covered by
  open PRs, so there is currently no clean entry issue for this proof.
- A maintainer reply / blessed issue before any PR or public post.
- A second dataset (e.g. a longer series, or one with a different
  seasonal pattern) would strengthen it; one series is a proof of
  skill, not of generality.
