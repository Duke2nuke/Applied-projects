"""Unsupervised anomaly detection on server metrics.

Method, in two steps:

1. Remove the daily cycle. Each point is compared with the median of
   the SAME HOUR OF DAY on previous days (up to 7 days back), giving a
   residual: how far this hour is from what this hour usually looks
   like. A trailing 24-hour window alone mixes peak and off-peak
   values and inflates the spread, so real spikes look ordinary;
   same-hour baselines remove that cycle first.
2. Score the residual robustly. Each residual is compared with the
   median and MAD (median absolute deviation) of the previous 24
   residuals. The modified z-score is 0.6745 * (residual - median) /
   MAD. Median/MAD are used instead of mean/std because one spike in
   the history cannot drag them the way it drags a mean, so spikes
   stand out instead of hiding in their own average.

A point is flagged if ANY metric's modified z-score exceeds the
threshold (5.0, a conventional robust-z cutoff). Points before hour
72 are a warm-up window and are never flagged: 48 hours to build
same-hour history, plus 24 residuals to estimate their spread.

Why not a fixed threshold like "CPU > 90%"? A latency of 300 ms can
be normal at peak and a symptom at 3 a.m.; comparing with the same
hour on previous days adapts to that.
"""

import numpy as np
import pandas as pd

FEATURES = ["cpu_percent", "memory_percent", "latency_ms", "requests_per_min"]
HISTORY_DAYS = 7
SEASONAL_WARMUP = 48  # need at least 2 same-hour observations
RESIDUAL_WINDOW = 24
WARMUP = SEASONAL_WARMUP + RESIDUAL_WINDOW  # 72
THRESHOLD = 5.0


def seasonal_residuals(values: np.ndarray, history_days: int = HISTORY_DAYS) -> np.ndarray:
    """Residual of each point vs the median of the same hour, previous days."""
    residuals = np.full(len(values), np.nan)
    for i in range(SEASONAL_WARMUP, len(values)):
        days_back = min(history_days, i // 24)
        history = values[[i - 24 * k for k in range(1, days_back + 1)]]
        residuals[i] = values[i] - np.median(history)
    return residuals


def modified_z_scores(values: np.ndarray, history_days: int = HISTORY_DAYS) -> np.ndarray:
    """Modified z-score of each point's seasonal residual vs prior residuals."""
    residuals = seasonal_residuals(values, history_days)
    scores = np.zeros(len(values))
    for i in range(WARMUP, len(values)):
        history = residuals[i - RESIDUAL_WINDOW : i]
        median = np.median(history)
        mad = np.median(np.abs(history - median))
        if mad == 0:  # flat history: fall back to std, else no signal
            mad = np.std(history) or 1.0
        scores[i] = 0.6745 * (residuals[i] - median) / mad
    return scores


def detect(df: pd.DataFrame, threshold: float = THRESHOLD) -> pd.DataFrame:
    """Return a copy of df with per-feature scores and a predicted flag."""
    out = df.copy()
    for feature in FEATURES:
        out[f"{feature}_z"] = modified_z_scores(df[feature].to_numpy())
    score_cols = [f"{f}_z" for f in FEATURES]
    out["max_abs_z"] = out[score_cols].abs().max(axis=1)
    out["predicted_anomaly"] = out["max_abs_z"] > threshold
    return out


def evaluate(result: pd.DataFrame) -> dict:
    """Precision/recall/F1 of predicted vs labelled anomalies."""
    actual = result["is_anomaly"].to_numpy()
    pred = result["predicted_anomaly"].to_numpy()
    tp = int((actual & pred).sum())
    fp = int((~actual & pred).sum())
    fn = int((actual & ~pred).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }
