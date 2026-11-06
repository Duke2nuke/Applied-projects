"""Day 11 — Daily Demand Forecaster (Day B: AI/ML Python).

Forecasts the next day's demand for a synthetic daily series (campus
canteen orders) with trend + weekly seasonality + noise. Compares three
models under walk-forward evaluation:

  * naive        — tomorrow = today
  * seasonal     — tomorrow = same weekday last week
  * ridge        — ridge regression on lags 1/7/14, day-of-week and trend

Standard library only. All data is synthetic and labelled as such.
"""

import math
import random

# ---------------------------------------------------------------- data ---

DAYS = 365          # one year of daily demand
SEED = 11


def generate_series(n=DAYS, seed=SEED):
    """Synthetic daily orders: base + trend + weekly seasonality + noise.

    Weekend demand is lower; a slow upward trend mimics a growing
    customer base. The generating process is known, so the README can
    say honestly what the model had to recover.
    """
    rng = random.Random(seed)
    out = []
    for t in range(n):
        dow = t % 7                     # 0 = Monday ... 6 = Sunday
        weekend = -28.0 if dow >= 5 else 0.0
        weekly = 12.0 * math.sin(2 * math.pi * dow / 7.0)
        value = 120.0 + 0.15 * t + weekend + weekly + rng.gauss(0, 8.0)
        out.append(max(20.0, value))
    return out


# -------------------------------------------------------------- models ---

def naive_forecast(series):
    """Tomorrow = today."""
    return series[-1]


def seasonal_naive_forecast(series, period=7):
    """Tomorrow = same weekday last week."""
    return series[-period]


def make_features(series, t):
    """Feature vector for forecasting day ``t`` from data before ``t``.

    [1, lag1, lag7, lag14, trend t, Mon..Sat one-hot (Sun = baseline)]
    """
    dow = t % 7
    one_hot = [1.0 if dow == d else 0.0 for d in range(6)]
    return [1.0, series[t - 1], series[t - 7], series[t - 14], float(t)] + one_hot


def _solve(a, b):
    """Solve a x = b by Gaussian elimination with partial pivoting."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        if abs(m[col][col]) < 1e-12:
            raise ValueError("singular matrix")
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            for c in range(col, n + 1):
                m[r][c] -= f * m[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (m[i][n] - sum(m[i][j] * x[j] for j in range(i + 1, n))) / m[i][i]
    return x


def fit_ridge(series, upto, alpha=10.0):
    """Fit ridge regression on days 14..upto-1, forecasting each from past.

    Returns the weight vector. The intercept is not penalised.
    """
    rows, ys = [], []
    for t in range(14, upto):
        rows.append(make_features(series, t))
        ys.append(series[t])
    k = len(rows[0])
    ata = [[0.0] * k for _ in range(k)]
    atb = [0.0] * k
    for row, y in zip(rows, ys):
        for i in range(k):
            atb[i] += row[i] * y
            for j in range(k):
                ata[i][j] += row[i] * row[j]
    for i in range(1, k):          # penalise everything but the intercept
        ata[i][i] += alpha
    return _solve(ata, atb)


def ridge_forecast(series, weights, t):
    """One-step forecast for day ``t`` using fitted weights."""
    return sum(w * f for w, f in zip(weights, make_features(series, t)))


# ---------------------------------------------------------- evaluation ---

def mae(errors):
    return sum(abs(e) for e in errors) / len(errors)


def rmse(errors):
    return math.sqrt(sum(e * e for e in errors) / len(errors))


def walk_forward(series, start=200, refit_every=30, alpha=10.0):
    """Expanding-window walk-forward eval from ``start`` to the end.

    Refit the ridge model every ``refit_every`` days on all data seen so
    far; baselines need no fitting. Returns {model: (mae, rmse)}.
    """
    errs = {"naive": [], "seasonal": [], "ridge": []}
    weights = None
    for t in range(start, len(series)):
        if weights is None or (t - start) % refit_every == 0:
            weights = fit_ridge(series, t, alpha=alpha)
        actual = series[t]
        errs["naive"].append(actual - naive_forecast(series[:t]))
        errs["seasonal"].append(actual - seasonal_naive_forecast(series[:t]))
        errs["ridge"].append(actual - ridge_forecast(series, weights, t))
    return {m: (mae(e), rmse(e)) for m, e in errs.items()}


def forecast_next_days(series, horizon=7, alpha=10.0):
    """Forecast the next ``horizon`` days, feeding predictions back in."""
    weights = fit_ridge(series, len(series), alpha=alpha)
    extended = list(series)
    out = []
    for i in range(horizon):
        t = len(extended)
        pred = ridge_forecast(extended, weights, t)
        out.append(pred)
        extended.append(pred)
    return out
