"""Drift Watch — data & prediction drift detector for a deployed tabular model.

Problem: a model trained on last quarter's data silently degrades when the
live data distribution moves (new customer mix, a changed form, an upstream
bug). Accuracy can fall weeks before anyone notices, because live labels
arrive late or never.

What it does: given a reference dataset (what the model was trained on) and
a current dataset (what it sees now), it reports, per feature and for the
model's own predictions:
  * PSI (Population Stability Index) — the industry-standard drift score
  * two-sample Kolmogorov–Smirnov test statistic and p-value
  * a severity verdict per feature: STABLE / WATCH / DRIFT
plus an overall verdict and the features driving the drift.

The demo trains a small logistic-regression loan-default model on synthetic
reference data, then scores a drifted "current" batch and shows which
features moved and by how much. All demo data is synthetic and labelled so.

Thresholds used (standard PSI practice):
  PSI < 0.10  -> STABLE   (no meaningful shift)
  0.10-0.25   -> WATCH    (small shift, keep an eye on it)
  PSI >= 0.25 -> DRIFT    (significant shift, investigate / retrain)

Usage:
    python drift_watch.py --demo                 # run the built-in demo
    python drift_watch.py --demo --out report.json
    python drift_watch.py --reference ref.csv --current cur.csv \
        --features income,age,credit_score,loan_amount,years_employed \
        --label default --out report.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys

import numpy as np
from scipy import stats

FEATURES = ["income", "age", "credit_score", "loan_amount", "years_employed"]

# PSI severity bands (standard practice).
PSI_STABLE_MAX = 0.10
PSI_WATCH_MAX = 0.25


# ---------------------------------------------------------------------------
# Synthetic data
# ---------------------------------------------------------------------------

def generate_data(n: int, seed: int, drift: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic loan-application rows.

    Columns: income ($k/yr), age, credit_score, loan_amount ($k),
    years_employed. Label: defaulted (1) or not (0), from a logistic rule
    plus noise. With drift=True the current batch shifts: lower income,
    wider credit-score spread, larger loans; age stays put as a control.
    """
    rng = np.random.default_rng(seed)
    income = rng.normal(55 if not drift else 42, 15, n)
    age = rng.normal(38, 11, n)
    credit_score = rng.normal(680, 60 if not drift else 110, n)
    loan_amount = rng.normal(18 if not drift else 26, 7, n)
    years_employed = rng.normal(6, 3.5, n)

    X = np.column_stack([income, age, credit_score, loan_amount, years_employed])
    X = np.clip(X, a_min=[5, 18, 300, 1, 0], a_max=[200, 80, 850, 80, 40])

    # True default rule: low income / low score / big loan / short employment
    # raise default risk; age is (deliberately) irrelevant.
    z = (
        -1.6
        - 0.045 * (X[:, 0] - 55)          # income
        - 0.012 * (X[:, 2] - 680)         # credit score
        + 0.055 * (X[:, 3] - 18)          # loan amount
        - 0.10 * X[:, 4]                  # years employed
    )
    p = 1.0 / (1.0 + np.exp(-z))
    y = (rng.random(n) < p).astype(int)
    return X, y


# ---------------------------------------------------------------------------
# Model: logistic regression trained from scratch (gradient descent)
# ---------------------------------------------------------------------------

def train_logistic_regression(
    X: np.ndarray, y: np.ndarray, lr: float = 0.1, epochs: int = 500
) -> dict:
    """Fit logistic regression with standardisation. Returns weights + scaler."""
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std = np.where(std == 0, 1.0, std)
    Xs = (X - mean) / std
    Xb = np.column_stack([np.ones(len(Xs)), Xs])
    w = np.zeros(Xb.shape[1])
    for _ in range(epochs):
        p = 1.0 / (1.0 + np.exp(-(Xb @ w)))
        grad = Xb.T @ (p - y) / len(y)
        w -= lr * grad
    return {"weights": w, "mean": mean, "std": std}


def predict_proba(model: dict, X: np.ndarray) -> np.ndarray:
    Xs = (X - model["mean"]) / model["std"]
    Xb = np.column_stack([np.ones(len(Xs)), Xs])
    return 1.0 / (1.0 + np.exp(-(Xb @ model["weights"])))


def accuracy(model: dict, X: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((predict_proba(model, X) >= 0.5).astype(int) == y))


# ---------------------------------------------------------------------------
# Drift statistics
# ---------------------------------------------------------------------------

def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index between two samples.

    Quantile bins are cut on the reference (expected) sample; each bin's
    share in both samples is compared. Identical distributions score ~0.
    """
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    quantiles = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    if len(quantiles) < 3:  # near-constant feature: fall back to a mean check
        return 0.0 if abs(expected.mean() - actual.mean()) < 1e-9 else 1.0
    e_counts, _ = np.histogram(expected, bins=quantiles)
    a_counts, _ = np.histogram(actual, bins=quantiles)
    e_perc = np.clip(e_counts / len(expected), 1e-4, None)
    a_perc = np.clip(a_counts / len(actual), 1e-4, None)
    return float(np.sum((a_perc - e_perc) * np.log(a_perc / e_perc)))


def ks_test(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Two-sample Kolmogorov–Smirnov test. Returns (statistic, p-value)."""
    res = stats.ks_2samp(a, b)
    return float(res.statistic), float(res.pvalue)


def severity(psi_value: float) -> str:
    if psi_value < PSI_STABLE_MAX:
        return "STABLE"
    if psi_value < PSI_WATCH_MAX:
        return "WATCH"
    return "DRIFT"


def drift_report(
    ref_X: np.ndarray,
    cur_X: np.ndarray,
    ref_pred: np.ndarray | None = None,
    cur_pred: np.ndarray | None = None,
    feature_names: list[str] | None = None,
) -> dict:
    """Per-feature + (optional) prediction drift report with overall verdict."""
    names = feature_names or FEATURES
    features = []
    for i, name in enumerate(names):
        p = psi(ref_X[:, i], cur_X[:, i])
        ks_stat, ks_p = ks_test(ref_X[:, i], cur_X[:, i])
        features.append(
            {
                "feature": name,
                "psi": round(p, 4),
                "ks_statistic": round(ks_stat, 4),
                "ks_pvalue": round(ks_p, 6),
                "ref_mean": round(float(ref_X[:, i].mean()), 3),
                "cur_mean": round(float(cur_X[:, i].mean()), 3),
                "severity": severity(p),
            }
        )
    severities = [f["severity"] for f in features]
    prediction = None
    if ref_pred is not None and cur_pred is not None:
        pred_psi = psi(ref_pred, cur_pred)
        pred_ks, pred_p = ks_test(ref_pred, cur_pred)
        prediction = {
            "psi": round(pred_psi, 4),
            "ks_statistic": round(pred_ks, 4),
            "ks_pvalue": round(pred_p, 6),
            "ref_mean_proba": round(float(ref_pred.mean()), 4),
            "cur_mean_proba": round(float(cur_pred.mean()), 4),
            "severity": severity(pred_psi),
        }
        severities.append(prediction["severity"])
    worst = max(severities, key=lambda s: {"STABLE": 0, "WATCH": 1, "DRIFT": 2}[s])
    drivers = [f["feature"] for f in features if f["severity"] == "DRIFT"]
    report: dict = {
        "features": features,
        "overall_verdict": worst,
        "drift_drivers": drivers,
        "n_reference": int(len(ref_X)),
        "n_current": int(len(cur_X)),
    }
    if prediction is not None:
        report["prediction"] = prediction
    return report


# ---------------------------------------------------------------------------
# Demo + CLI
# ---------------------------------------------------------------------------

def run_demo() -> dict:
    ref_X, ref_y = generate_data(3000, seed=42, drift=False)
    cur_X, cur_y = generate_data(1500, seed=7, drift=True)
    model = train_logistic_regression(ref_X, ref_y)
    report = drift_report(
        ref_X, cur_X,
        predict_proba(model, ref_X), predict_proba(model, cur_X),
    )
    report["model"] = {
        "type": "logistic regression (from scratch, numpy gradient descent)",
        "train_accuracy": round(accuracy(model, ref_X, ref_y), 4),
        "current_accuracy": round(accuracy(model, cur_X, cur_y), 4),
        "reference_default_rate": round(float(ref_y.mean()), 4),
        "current_default_rate": round(float(cur_y.mean()), 4),
    }
    return report


def load_csv(path: str) -> tuple[np.ndarray, list[str]]:
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    names = list(rows[0].keys())
    return np.array([[float(r[n]) for n in names] for r in rows]), names


def print_report(report: dict) -> None:
    print(f"\nDrift Watch — reference n={report['n_reference']}, "
          f"current n={report['n_current']}")
    print(f"{'feature':<16}{'PSI':>8}{'KS stat':>9}{'KS p':>10}{'ref mean':>10}"
          f"{'cur mean':>10}  verdict")
    for f in report["features"]:
        print(f"{f['feature']:<16}{f['psi']:>8.4f}{f['ks_statistic']:>9.4f}"
              f"{f['ks_pvalue']:>10.6f}{f['ref_mean']:>10.3f}"
              f"{f['cur_mean']:>10.3f}  {f['severity']}")
    p = report.get("prediction")
    if p is not None:
        print(f"{'PREDICTION':<16}{p['psi']:>8.4f}{p['ks_statistic']:>9.4f}"
              f"{p['ks_pvalue']:>10.6f}{p['ref_mean_proba']:>10.4f}"
              f"{p['cur_mean_proba']:>10.4f}  {p['severity']}")
    if "model" in report:
        m = report["model"]
        print(f"\nModel: {m['type']}")
        print(f"  train accuracy {m['train_accuracy']}, "
              f"current-batch accuracy {m['current_accuracy']}")
        print(f"  default rate {m['reference_default_rate']} -> "
              f"{m['current_default_rate']}")
    print(f"\nOverall verdict: {report['overall_verdict']}")
    if report["drift_drivers"]:
        print("Drift drivers: " + ", ".join(report["drift_drivers"]))
    else:
        print("No drift drivers.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Drift Watch — drift detector")
    ap.add_argument("--demo", action="store_true", help="run the built-in demo")
    ap.add_argument("--reference", help="reference CSV (training-time data)")
    ap.add_argument("--current", help="current CSV (live data)")
    ap.add_argument("--features", help="comma-separated feature columns")
    ap.add_argument("--label", help="label column (excluded from drift check)")
    ap.add_argument("--out", help="write JSON report to this file")
    args = ap.parse_args(argv)

    if args.demo or not (args.reference and args.current):
        report = run_demo()
    else:
        ref, ref_names = load_csv(args.reference)
        cur, cur_names = load_csv(args.current)
        names = args.features.split(",") if args.features else [
            n for n in ref_names if n != args.label]
        ref_idx = [ref_names.index(n) for n in names]
        cur_idx = [cur_names.index(n) for n in names]
        # CSV mode compares feature distributions only — prediction drift
        # needs the trained model, which lives in --demo.
        report = drift_report(ref[:, ref_idx], cur[:, cur_idx],
                              feature_names=names)
        report["note"] = ("CSV mode compares feature distributions only; "
                          "run --demo for the full model + prediction drift.")
    print_report(report)
    if args.out:
        with open(args.out, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport written to {args.out}")
    return 0 if report["overall_verdict"] == "STABLE" else 1


if __name__ == "__main__":
    sys.exit(main())
