# Day 29 — Drift Watch: Data & Prediction Drift Detector (Day B: AI/ML Python)

Detect when the data a deployed model sees has moved away from the data it
was trained on — before the damage shows up as silent accuracy loss.

## The problem

A loan-default model trained last quarter keeps serving predictions, but the
world moved: applicants now earn less, ask for bigger loans, and credit
scores spread wider. Live labels arrive weeks late (or never), so accuracy
can't be watched directly. What *can* be watched is the input distribution
and the model's own prediction distribution — if those moved, the model is
almost certainly degrading.

## What it does

Given a reference dataset (training-time data) and a current dataset (live
data), Drift Watch reports per feature and for the model's predictions:

- **PSI (Population Stability Index)** — the industry-standard drift score,
  computed on quantile bins cut from the reference sample
- **Two-sample Kolmogorov–Smirnov test** — statistic + p-value
- **Severity verdict** — STABLE / WATCH / DRIFT, using standard PSI bands
  (PSI < 0.10 stable, 0.10–0.25 watch, ≥ 0.25 drift)
- **Overall verdict + drift drivers** — which features moved

The demo trains a small logistic-regression loan-default model from scratch
(numpy gradient descent, no sklearn) on 3,000 synthetic reference rows, then
scores a 1,500-row drifted "current" batch.

## Results (actually run, 24 Nov 2026)

```
feature              PSI  KS stat      KS p  ref mean  cur mean  verdict
income            0.7715   0.3743  0.000000    54.619    41.185  DRIFT
age               0.0073   0.0273  0.441265    38.245    38.068  STABLE
credit_score      0.3211   0.1493  0.000000   679.740   677.889  DRIFT
loan_amount       1.2337   0.4597  0.000000    17.835    26.001  DRIFT
years_employed    0.0128   0.0337  0.205524     6.050     5.847  STABLE
PREDICTION        0.4916   0.3180  0.000000    0.1463    0.2977  DRIFT

Model: train accuracy 0.8633, current-batch accuracy 0.762
       default rate 0.1427 -> 0.3167
Overall verdict: DRIFT — drivers: income, credit_score, loan_amount
```

The detector catches exactly the three drifted features and leaves the two
stable ones alone — including `age`, planted as a control that never moves.
The drift is not cosmetic: mean predicted default probability doubles
(0.146 → 0.298) and the model's accuracy falls 0.863 → 0.762 on the drifted
batch. Note `credit_score` is flagged on PSI (0.32) even though its mean
barely moved (679.7 → 677.9) — its *spread* widened, which a mean-only check
would miss. That is the point of PSI.

**Tests: 16/16 pass** (`python -m unittest test_drift_watch`), covering PSI
bands, KS behaviour, severity thresholds, model quality (AUC 0.769 — the
synthetic labels are noisy by design, so this is the ceiling, not a failure),
end-to-end demo determinism, and the CLI (exit code 1 on DRIFT, so it can
gate a CI pipeline).

## How to run

```bash
pip install -r requirements.txt
python drift_watch.py --demo                    # built-in demo, prints report
python drift_watch.py --demo --out report.json  # also writes JSON report
python drift_watch.py --reference ref.csv --current cur.csv \
    --features income,age,credit_score,loan_amount,years_employed
```

CSV mode compares feature distributions only; the full model + prediction
drift needs `--demo` (or your own trained model wired in).

## 2-minute explainer

**Problem:** deployed models degrade silently when live data drifts from
training data, and labels arrive too late to catch it by watching accuracy.
**Approach:** compare the reference and current distributions feature by
feature with PSI on reference-quantile bins plus a KS test, and do the same
for the model's predicted probabilities — if the predictions moved, the
model's behaviour moved. A logistic regression is trained from scratch with
numpy so the whole pipeline is transparent. **Results:** on synthetic data
with three planted shifts, the detector flags exactly those three features
(PSI 0.32–1.23) and the prediction distribution (PSI 0.49), while the
control features stay STABLE; accuracy on the drifted batch drops 0.86 to
0.76, confirming the drift is real damage, not a false alarm. **Limits:**
synthetic data with known, planted drift — on real data, PSI needs a
representative reference sample and sensible binning, and drift alone
doesn't prove *which* upstream change caused it; it tells you where to look.
It also doesn't retrain anything — it is a monitor, not a fix.

## Why this matters

Model monitoring / drift detection is a standard part of ML observability
and evals work — the skill that shows up in most agent/AI-engineer job
postings. This is the smallest honest version of it: two statistics, a
verdict, and a CLI exit code a pipeline can act on.

## Files

- `drift_watch.py` — data generation, logistic regression, PSI/KS, report, CLI
- `test_drift_watch.py` — 16 tests
- `requirements.txt` — numpy, scipy
- `results.json` — the demo report, as actually run
