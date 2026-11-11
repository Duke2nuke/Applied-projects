"""scikit-learn evaluation classifier — proof project (local only).

Dataset: scikit-learn built-in breast_cancer (569 samples, 30 features,
binary target: 0 = malignant, 1 = benign). Real dataset, not hand-written
synthetic data. Not a real-world deployment.

Models (both as pipelines, fixed random_state=42 throughout):
  - LogisticRegression (with StandardScaler, max_iter=1000)
  - RandomForestClassifier (n_estimators=200)

Evaluation: stratified 80/20 train/test split (random_state=42),
5-fold stratified cross-validation on the training set, then on the
held-out test set: accuracy, precision, recall, F1 (macro), confusion
matrix, and the full classification report.

Run:  python sklearn_eval.py
Output: metrics.json (exact numbers) + a printed summary.
"""

import json
from pathlib import Path

import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RANDOM_STATE = 42
HERE = Path(__file__).resolve().parent


def load_data():
    """Load the built-in breast_cancer dataset. Returns X, y, target names."""
    data = load_breast_cancer()
    return data.data, data.target, list(data.target_names)


def make_models():
    return {
        "logistic_regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
                ),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1
                    ),
                ),
            ]
        ),
    }


def evaluate_model(model, X_train, X_test, y_train, y_test, target_names):
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_accuracy = cross_val_score(model, X_train, y_train, cv=cv, scoring="accuracy")
    cv_f1 = cross_val_score(model, X_train, y_train, cv=cv, scoring="f1_macro")
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    return {
        "cv_accuracy_mean": float(cv_accuracy.mean()),
        "cv_accuracy_std": float(cv_accuracy.std()),
        "cv_f1_macro_mean": float(cv_f1.mean()),
        "cv_f1_macro_std": float(cv_f1.std()),
        "test_accuracy": float(accuracy_score(y_test, y_pred)),
        "test_precision_macro": float(
            precision_score(y_test, y_pred, average="macro", zero_division=0)
        ),
        "test_recall_macro": float(
            recall_score(y_test, y_pred, average="macro", zero_division=0)
        ),
        "test_f1_macro": float(f1_score(y_test, y_pred, average="macro")),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(
            y_test, y_pred, target_names=target_names, output_dict=True
        ),
        "classification_report_text": classification_report(
            y_test, y_pred, target_names=target_names
        ),
        "n_test": int(len(y_test)),
    }


def main():
    X, y, target_names = load_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    results = {
        "dataset": "sklearn.datasets.load_breast_cancer",
        "n_samples": int(X.shape[0]),
        "n_features": int(X.shape[1]),
        "target_names": target_names,
        "train_size": int(len(y_train)),
        "test_size": int(len(y_test)),
        "random_state": RANDOM_STATE,
        "test_size_fraction": 0.2,
        "cv_folds": 5,
        "models": {},
    }
    for name, model in make_models().items():
        results["models"][name] = evaluate_model(
            model, X_train, X_test, y_train, y_test, target_names
        )
    out = HERE / "metrics.json"
    out.write_text(json.dumps(results, indent=2))

    for name, m in results["models"].items():
        print(f"\n== {name} ==")
        print(f"  CV accuracy:  {m['cv_accuracy_mean']:.4f} +- {m['cv_accuracy_std']:.4f}")
        print(f"  CV F1 macro:  {m['cv_f1_macro_mean']:.4f} +- {m['cv_f1_macro_std']:.4f}")
        print(f"  Test accuracy: {m['test_accuracy']:.4f}")
        print(f"  Test precision (macro): {m['test_precision_macro']:.4f}")
        print(f"  Test recall (macro):    {m['test_recall_macro']:.4f}")
        print(f"  Test F1 (macro):        {m['test_f1_macro']:.4f}")
        print(f"  Confusion matrix (rows=true, cols=pred): {m['confusion_matrix']}")
        print(m["classification_report_text"])
    print(f"Wrote {out}")
    return results


if __name__ == "__main__":
    main()
