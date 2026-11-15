# Churn Predictor — Day 20 (Day B: AI/ML Python)

Which telecom subscribers are about to leave, and why — so a retention
team knows who to call first and what to offer them.

## What it does

- Generates 3,000 **synthetic** telecom customers (seeded RNG, no real
  data, nothing downloaded) with tenure, charges, contract, internet
  service, payment method, tech support and support-call history.
  Churn is planted with an explainable signal: short tenure,
  month-to-month contracts, expensive fibre plans, electronic-check
  billing, no tech support and repeated support calls all raise churn
  risk.
- Stratified 80/20 train/test split; a `ColumnTransformer` scales the
  numeric features and one-hot-encodes the categoricals (fit on train
  only, so there is no leakage).
- Trains Logistic Regression (`class_weight="balanced"`) and Random
  Forest (300 trees, `class_weight="balanced_subsample"`) and compares
  them on ROC-AUC and PR-AUC — not accuracy, because only 32% churn.
- Reports the top churn drivers per model and prints a **retention
  outreach list**: the 10 customers with the highest predicted churn
  probability, with their contract, charges and support history.

## Results (actually run, 15 Nov 2026 — see `metrics.json`)

Test set: 600 customers, 193 churned. Predicting "nobody churns" scores
67.8% accuracy and catches zero churners.

| model | ROC-AUC | PR-AUC | acc | prec | rec | F1 |
|---|---|---|---|---|---|---|
| logistic regression | 0.808 | 0.681 | 0.737 | 0.579 | 0.663 | 0.618 |
| random forest | 0.772 | 0.619 | 0.748 | 0.659 | 0.451 | 0.535 |

Logistic regression wins on ROC-AUC and recall; random forest wins on
precision. Top drivers agree with the planted signal in both models:
month-to-month contract, two-year contract (protective), monthly
charges, tenure, electronic-check payment and support-call count.

The riskiest customer (p = 0.983) is a 9-month, $95.27/mo fibre
subscriber on month-to-month billing with no tech support and 6 support
calls — exactly the profile a retention team would want to call first.

## How to run

```bash
pip install -r requirements.txt
python run.py            # generate data, train, print report, write metrics.json
python -m pytest test_churn.py -v   # 8 tests
```

## Limits

- The data is synthetic with a planted signal, so the scores prove the
  pipeline works — they are not a real-world churn rate or a claim
  about any real telecom's customers.
- Logistic regression assumes roughly linear log-odds; random forest
  captures interactions but is less interpretable. Neither model knows
  anything the features don't contain (no usage, complaint-text or
  competitor-offer data).
- The 0.5 decision threshold is a default, not a business choice: a
  retention team that can afford more calls would lower it to trade
  precision for recall, the same way Day 17 tuned its fraud threshold.

## 2-minute explainer

**Problem:** a telecom loses about a third of the customers in this
sample, and retention calls are expensive, so the team needs to know
*who* is about to leave and *why*, not just an overall churn rate.

**Approach:** I built a synthetic customer table with the drivers a
retention team can act on, then trained two classifiers behind one
preprocessing pipeline — logistic regression for interpretability and
random forest for non-linear patterns — and compared them on ROC-AUC
and PR-AUC instead of accuracy, since churn is the minority class.

**Results:** logistic regression reaches ROC-AUC 0.81 and catches 66%
of churners; both models recover the planted drivers — month-to-month
contracts, high monthly charges, short tenure and repeated support
calls. The output is a ranked top-10 at-risk list the team can call
first.

**Limits:** the data is synthetic, so these numbers validate the
pipeline, not a real churn model; and the threshold is a default, not a
cost-tuned business decision.
