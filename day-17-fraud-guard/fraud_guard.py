"""Fraud-Guard: imbalanced binary classification on synthetic transactions.

Teaches the one thing most intro ML projects skip: when the positive class
is rare (here ~3% "fraud"), accuracy is a useless metric and the decision
threshold is a business choice, not a default.

Pipeline
--------
1. Generate a synthetic, clearly labelled transaction dataset
   (``make_classification``, 3% fraud) — no real data, no downloads.
2. Stratified train/test split, StandardScaler fit on train only.
3. Train two models with class weights that counter the imbalance:
   Logistic Regression and Random Forest.
4. Evaluate at the default 0.5 threshold AND after tuning the threshold
   on the precision-recall curve to hit recall >= 0.80 with the best
   precision possible.
5. Print a comparison table and write ``metrics.json``.

Run:  python run.py
"""

import json

import numpy as np
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score,
                             confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

RANDOM_STATE = 42
N_SAMPLES = 10_000
FRAUD_RATE = 0.03          # 3% positives — the imbalance this project is about
TARGET_RECALL = 0.80       # threshold is tuned to reach at least this recall


def generate_data(n_samples=N_SAMPLES, fraud_rate=FRAUD_RATE,
                  random_state=RANDOM_STATE):
    """Synthetic transactions: 20 numeric features, ~3% fraud.

    Returns X (ndarray), y (ndarray of 0/1). Nothing here is real data.
    """
    X, y = make_classification(
        n_samples=n_samples,
        n_features=20,
        n_informative=8,
        n_redundant=4,
        n_clusters_per_class=2,
        weights=[1 - fraud_rate, fraud_rate],
        class_sep=1.5,
        flip_y=0.01,
        random_state=random_state,
    )
    return X, y


def split_data(X, y, random_state=RANDOM_STATE):
    """Stratified 80/20 split so both sets keep the ~3% fraud rate."""
    return train_test_split(X, y, test_size=0.2, stratify=y,
                            random_state=random_state)


def build_models():
    """Two baselines that handle imbalance differently."""
    return {
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(class_weight="balanced", max_iter=1000,
                               random_state=RANDOM_STATE),
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200, class_weight="balanced_subsample",
            random_state=RANDOM_STATE, n_jobs=-1,
        ),
    }


def tune_threshold(y_true, proba, target_recall=TARGET_RECALL):
    """Pick the highest threshold whose recall is still >= target_recall.

    Scans every distinct predicted probability (descending). Among the
    thresholds meeting the recall target, the highest one gives the best
    precision — fewer false alarms for the same catch rate.
    """
    order = np.argsort(proba)[::-1]
    y_sorted = np.asarray(y_true)[order]
    total_pos = int(np.sum(y_true))
    best = {"threshold": 0.5, "precision": 0.0, "recall": 0.0}
    for i, idx in enumerate(order):
        tp = int(np.sum(y_sorted[: i + 1] == 1))
        recall = tp / total_pos
        precision = tp / (i + 1)
        if recall >= target_recall:
            best = {"threshold": float(proba[idx]),
                    "precision": float(precision),
                    "recall": float(recall)}
            break
    return best


def evaluate(model, X_test, y_test):
    """Metrics at the default 0.5 threshold plus the recall-tuned one."""
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    tuned = tune_threshold(y_test, proba)
    tuned_pred = (proba >= tuned["threshold"]).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
    return {
        "accuracy": float(accuracy_score(y_test, pred)),
        "precision@0.5": float(precision_score(y_test, pred, zero_division=0)),
        "recall@0.5": float(recall_score(y_test, pred, zero_division=0)),
        "f1@0.5": float(f1_score(y_test, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, proba)),
        "pr_auc": float(average_precision_score(y_test, proba)),
        "confusion@0.5": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "tuned_threshold": tuned["threshold"],
        "precision@tuned": tuned["precision"],
        "recall@tuned": tuned["recall"],
        "f1@tuned": float(f1_score(y_test, tuned_pred, zero_division=0)),
    }


def run_pipeline():
    """Full run: data -> models -> metrics dict (also printed by run.py)."""
    X, y = generate_data()
    X_train, X_test, y_train, y_test = split_data(X, y)
    results = {
        "dataset": {
            "n_samples": int(len(y)),
            "n_features": int(X.shape[1]),
            "fraud_rate": float(np.mean(y)),
            "train_size": int(len(y_train)),
            "test_size": int(len(y_test)),
            "test_fraud": int(np.sum(y_test)),
            "target_recall": TARGET_RECALL,
            "synthetic": True,
        }
    }
    for name, model in build_models().items():
        model.fit(X_train, y_train)
        results[name] = evaluate(model, X_test, y_test)
    return results


def main():
    results = run_pipeline()
    d = results["dataset"]
    print(f"Fraud-Guard — synthetic transactions: {d['n_samples']} rows, "
          f"{d['fraud_rate']:.1%} fraud, test set {d['test_size']} rows "
          f"({d['test_fraud']} fraud)")
    print(f"Naive 'predict everything legit' accuracy would be "
          f"{1 - d['fraud_rate']:.1%} — that is why accuracy is not the metric here.\n")
    header = (f"{'model':<22}{'acc':>7}{'prec@.5':>9}{'rec@.5':>8}"
              f"{'F1@.5':>7}{'ROC-AUC':>9}{'PR-AUC':>8}"
              f"{'thr':>7}{'prec@tuned':>11}{'rec@tuned':>10}")
    print(header)
    for name in ("logistic_regression", "random_forest"):
        m = results[name]
        print(f"{name:<22}{m['accuracy']:>7.4f}{m['precision@0.5']:>9.4f}"
              f"{m['recall@0.5']:>8.4f}{m['f1@0.5']:>7.4f}"
              f"{m['roc_auc']:>9.4f}{m['pr_auc']:>8.4f}"
              f"{m['tuned_threshold']:>7.3f}{m['precision@tuned']:>11.4f}"
              f"{m['recall@tuned']:>10.4f}")
    print(f"\nThreshold tuned for recall >= {TARGET_RECALL}: "
          f"catching 80%+ of fraud costs precision — that trade-off is the point.")
    with open("metrics.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("Wrote metrics.json")
    return results


if __name__ == "__main__":
    main()
