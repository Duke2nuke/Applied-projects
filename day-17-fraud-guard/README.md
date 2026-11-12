# Fraud-Guard — Day 17 (Day B: AI/ML Python)

Imbalanced binary classification on **synthetic** transaction data: only
~3% of transactions are fraud, so accuracy lies and the decision threshold
is a business choice, not a default. Two models are compared at the default
0.5 threshold and again after tuning the threshold to catch at least 80% of
fraud.

## What it does

- Generates 10,000 synthetic transactions (20 numeric features, 3.35%
  fraud) with `sklearn.datasets.make_classification` — **no real data**,
  nothing downloaded.
- Stratified 80/20 train/test split, scaler fit on train only.
- Trains Logistic Regression (`class_weight="balanced"`) and Random Forest
  (200 trees, `class_weight="balanced_subsample"`).
- Reports accuracy, precision, recall, F1, ROC-AUC and PR-AUC at threshold
  0.5, then re-tunes the threshold on the precision–recall curve to hit
  recall ≥ 0.80 with the best precision possible, and reports the tuned
  numbers too.

## Results (actually run, 12 Nov 2026 — see `metrics.json`)

Test set: 2,000 transactions, 67 fraud. A model that predicts "everything
is legit" scores 96.7% accuracy — and catches zero fraud.

| model | acc | prec@0.5 | rec@0.5 | F1@0.5 | ROC-AUC | PR-AUC | tuned thr | prec@tuned | rec@tuned |
|---|---|---|---|---|---|---|---|---|---|
| logistic regression | 0.773 | 0.118 | 0.896 | 0.209 | 0.896 | 0.276 | 0.544 | 0.122 | 0.806 |
| random forest | 0.974 | 0.941 | 0.239 | 0.381 | 0.960 | 0.671 | 0.085 | 0.415 | 0.806 |

The honest story is in the trade-off, not the headline numbers:

- **At 0.5, logistic regression catches 89.6% of fraud but cries wolf
  447 times** (precision 0.118). Random forest is the opposite: 94%
  precise but catches only 23.9% of fraud (51 of 67 slip through).
- **Tuned to recall ≥ 0.80, random forest is the usable model**:
  threshold 0.085, precision 0.415, F1 0.535 — it catches 54 of 67 fraud
  cases with roughly 1 in 2.4 flags being real. Logistic regression barely
  moves (threshold 0.544, precision 0.122): its scores are too flat to
  separate the classes well.
- **PR-AUC is the metric that matters here** (random baseline = fraud rate
  ≈ 0.03): random forest 0.671 vs logistic regression 0.276. ROC-AUC
  (0.960 vs 0.896) flatters both, because it rewards correctly ranking
  the 97% easy negatives.

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py            # prints the comparison table, writes metrics.json
python -m unittest test_fraud_guard -v   # 6 tests
```

## Files

- `fraud_guard.py` — data generation, models, threshold tuning, evaluation
- `run.py` — entry point
- `test_fraud_guard.py` — 6 tests (data shape/imbalance, stratification,
  reproducibility, threshold-tuning behaviour, full-pipeline sanity)
- `metrics.json` — metrics from the actual run above
- `requirements.txt` — scikit-learn, pandas, numpy

## Limits

- Synthetic data: class separation and noise are chosen by me, so the
  absolute scores say nothing about real fraud detection. The *method*
  (PR-AUC over accuracy, threshold tuning, class weights) is what transfers.
- No cost model: in production the threshold should be set from the real
  cost of a missed fraud vs a false alarm, not from an arbitrary 0.80
  recall target.
- No calibration, no drift monitoring, no explainability — a real system
  needs all three before it touches money.

## 2-minute explainer

**Problem:** fraud is rare — about 3 in 100 transactions — so a model can
score 97% accuracy by predicting "legit" every time and still be useless.
The real question is how many fraud cases you catch, and how many innocent
customers you bother, per flag.

**Approach:** I generated 10,000 synthetic transactions, split them
stratified so both halves keep the 3% fraud rate, and trained two models
with class weights that compensate for the imbalance. I evaluated both at
the default 0.5 threshold and again after tuning the threshold along the
precision–recall curve to guarantee at least 80% recall.

**Results:** at 0.5, logistic regression catches most fraud but with 12%
precision, while random forest is 94% precise but misses three-quarters of
fraud. After tuning, random forest at threshold 0.085 catches 80.6% of
fraud at 41.5% precision (PR-AUC 0.67) — the best operating point, and the
one I'd ship behind a human review queue.

**Limits:** the data is synthetic, so these scores don't transfer to real
fraud; the threshold target (80% recall) is arbitrary without a real cost
model; and a production system would still need calibration, drift
monitoring and explanations for each flag.
