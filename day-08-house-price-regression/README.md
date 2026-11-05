# Day 08 — House Price Predictor with Linear Regression, from Scratch (Day B: AI/ML Python)

Predict a house price from size, bedrooms, age, and distance to the city
centre — with linear regression implemented from scratch in pure Python:
no scikit-learn, no NumPy. Standardisation, batch gradient descent, and
the exact closed-form solution (normal equations + Gaussian elimination)
are all written out in `regression.py`, so every step can be explained,
not just called.

This is deliberately different from the earlier ML projects: Day 01 was
a supervised **classifier** (benign vs injection), Day 02 an **anomaly
detector**, Day 03 a **similarity matcher**, and Day 05 **unsupervised
clustering** (K-means). This one is **supervised regression** — the
target is a continuous number, not a label, a cluster, or a ranking —
and its extra twist is checking the iterative solver against the exact
solver, so "did gradient descent actually converge?" has an answer,
not a hope.

All data is **synthetic demo data, clearly labelled as such** (see
`data.py`). It is not real house prices, and the dollar figures below
are not market claims.

## How to run

No dependencies — Python 3.10+ standard library only.

```bash
python3 run.py              # train + test report
python3 test_regression.py  # automated checks
```

## Example output (actually run, 3 Nov 2026)

```
Gradient descent: intercept=$52,113
    size_sqft    $     150.0 per unit
    bedrooms     $  11,029.5 per unit
    age_years    $    -703.0 per unit
    distance_km  $  -2,135.8 per unit
    test MAE=$12,279  RMSE=$15,261  R^2=0.980
Closed form     : intercept=$52,113
    size_sqft    $     150.0 per unit
    bedrooms     $  11,029.5 per unit
    age_years    $    -703.0 per unit
    distance_km  $  -2,135.8 per unit
    test MAE=$12,279  RMSE=$15,261  R^2=0.980

True model    : intercept=$50,000
    size_sqft    $     150.0 per unit
    bedrooms     $  12,000.0 per unit
    age_years    $    -800.0 per unit
    distance_km  $  -2,000.0 per unit

Train n=160, test n=40; noise sigma=$15,000 (see data.py).
```

Two things worth noticing. First, gradient descent and the closed form
agree to within a fraction of a dollar on every test prediction — the
iterative solver really did converge. Second, the recovered weights are
close to the known true weights (size exactly $150/sq ft; bedrooms,
age, and distance within sampling noise of the truth), which is a
stronger check than R² alone: the model found the right relationship,
not just a good fit.

Tests (`python3 test_regression.py`, all 5 passing):

```
All 5 checks passed: GD-vs-closed-form mean diff=$0, test R^2=0.980, MAE=$12,279
```

## 2-minute interview explainer

**Problem.** Given a house's size, bedroom count, age, and distance to
the centre, predict its price — a continuous number, where being
$12k off on average matters more than getting a label right.

**Approach.** (1) Standardise every feature to zero mean and unit
variance, fitted on train only — otherwise size (500–3,000) would swamp
bedrooms (1–5) and no single learning rate would work. (2) Fit by batch
gradient descent on mean squared error (learning rate 0.05, 2,000
epochs). (3) Fit again with the closed-form normal equations, solved
by Gaussian elimination, and compare: agreement proves convergence.
(4) Convert coefficients back to original units for reporting, and
evaluate on a held-out 40-house test set the model never trained on.

**Results.** Test R² = 0.980, MAE = $12,279, RMSE = $15,261 — about the
noise level built into the synthetic data ($15,000), which is exactly
where a correct linear model should land. Recovered coefficients match
the true generating weights closely.

**Limits.** The data is synthetic and perfectly linear by
construction, so real prices — location effects, non-linear size
effects, market timing — would break this model. It has no
regularisation, no categorical features (neighbourhood, property type),
and no handling of outliers; a real version would need those, plus
real data, before any price claim could be made.

## Files

- `data.py` — synthetic generator (known true weights + noise) and split
- `regression.py` — scaler, gradient descent, closed form, metrics
- `run.py` — train/test report
- `test_regression.py` — 5 automated checks
- `requirements.txt` — empty on purpose (stdlib only)
