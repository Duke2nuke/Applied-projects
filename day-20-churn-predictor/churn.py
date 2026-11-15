"""Customer churn prediction: which subscribers are about to leave, and why.

Two models (logistic regression and random forest) are trained on the
synthetic telecom data from generate_data.py and compared on ROC-AUC and
PR-AUC. The output is a retention list: the customers with the highest
predicted churn probability, plus the churn drivers a retention team can
act on (contract type, support, price).
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from generate_data import generate

NUMERIC = ["tenure_months", "monthly_charges", "total_charges",
           "senior_citizen", "partner", "dependents", "support_calls"]
CATEGORICAL = ["contract", "internet_service", "payment_method",
               "tech_support"]
TARGET = "churn"


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("num", StandardScaler(), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])


def build_models() -> dict[str, Pipeline]:
    return {
        "logistic-regression": Pipeline([
            ("prep", build_preprocessor()),
            ("clf", LogisticRegression(class_weight="balanced",
                                       max_iter=1000, random_state=42)),
        ]),
        "random-forest": Pipeline([
            ("prep", build_preprocessor()),
            ("clf", RandomForestClassifier(n_estimators=300,
                                           class_weight="balanced_subsample",
                                           random_state=42, n_jobs=-1)),
        ]),
    }


def evaluate(model, X_test, y_test) -> dict:
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
    return {
        "accuracy": round(accuracy_score(y_test, pred), 4),
        "precision": round(precision_score(y_test, pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, pred, zero_division=0), 4),
        "f1": round(f1_score(y_test, pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, proba), 4),
        "pr_auc": round(average_precision_score(y_test, proba), 4),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def top_drivers(model, top_n: int = 8) -> list[dict]:
    """Feature importances / coefficients, mapped back to feature names."""
    prep = model.named_steps["prep"]
    names = list(prep.get_feature_names_out())
    clf = model.named_steps["clf"]
    if hasattr(clf, "feature_importances_"):
        scores = clf.feature_importances_
    else:  # logistic regression: absolute coefficients
        scores = np.abs(clf.coef_[0])
    order = np.argsort(scores)[::-1][:top_n]
    return [{"feature": names[i], "score": round(float(scores[i]), 4)}
            for i in order]


def at_risk_list(model, X_test, top_n: int = 10) -> list[dict]:
    """Highest-churn-probability customers, as a retention outreach list."""
    proba = model.predict_proba(X_test)[:, 1]
    idx = np.argsort(proba)[::-1][:top_n]
    rows = []
    for i in idx:
        row = X_test.iloc[i].to_dict()
        rows.append({
            "churn_probability": round(float(proba[i]), 3),
            "tenure_months": int(row["tenure_months"]),
            "monthly_charges": float(row["monthly_charges"]),
            "contract": row["contract"],
            "internet_service": row["internet_service"],
            "tech_support": row["tech_support"],
            "support_calls": int(row["support_calls"]),
        })
    return rows


def run(seed: int = 42) -> dict:
    df = generate(seed=seed)
    X = df[NUMERIC + CATEGORICAL]
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=seed)

    results: dict = {
        "n_customers": len(df),
        "churn_rate": round(float(y.mean()), 4),
        "test_size": len(y_test),
        "test_churn": int(y_test.sum()),
        "models": {},
    }
    best_name, best_auc = None, -1.0
    for name, model in build_models().items():
        model.fit(X_train, y_train)
        results["models"][name] = evaluate(model, X_test, y_test)
        results["models"][name]["top_drivers"] = top_drivers(model)
        if results["models"][name]["roc_auc"] > best_auc:
            best_auc = results["models"][name]["roc_auc"]
            best_name = name
    best_model = build_models()[best_name]
    best_model.fit(X_train, y_train)
    results["best_model"] = best_name
    results["at_risk_top10"] = at_risk_list(best_model, X_test)
    return results


def print_report(results: dict) -> None:
    print(f"Customers: {results['n_customers']} | "
          f"churn rate: {results['churn_rate']:.1%} | "
          f"test set: {results['test_size']} ({results['test_churn']} churned)")
    print(f"Baseline (predict nobody churns): "
          f"accuracy {1 - results['test_churn'] / results['test_size']:.3f}, "
          f"recall 0.000")
    for name, m in results["models"].items():
        print(f"\n{name}: ROC-AUC {m['roc_auc']} | PR-AUC {m['pr_auc']} | "
              f"acc {m['accuracy']} | prec {m['precision']} | "
              f"rec {m['recall']} | F1 {m['f1']}")
        print(f"  confusion: {m['confusion']}")
        print("  top drivers: " + ", ".join(
            f"{d['feature']} ({d['score']})" for d in m["top_drivers"]))
    print(f"\nBest model: {results['best_model']} — top 10 at-risk customers "
          f"(retention outreach list):")
    for r in results["at_risk_top10"]:
        print(f"  p={r['churn_probability']:.3f} | tenure "
              f"{r['tenure_months']}mo | ${r['monthly_charges']}/mo | "
              f"{r['contract']} | {r['internet_service']} | "
              f"tech_support={r['tech_support']} | "
              f"{r['support_calls']} support calls")


if __name__ == "__main__":
    res = run()
    with open("metrics.json", "w") as f:
        json.dump(res, f, indent=2)
    print_report(res)
    print("\nWrote metrics.json")
