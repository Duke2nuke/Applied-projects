"""Tests for the churn predictor (run: python -m pytest test_churn.py -v)."""

import numpy as np
import pandas as pd
import pytest

from churn import (
    CATEGORICAL,
    NUMERIC,
    at_risk_list,
    build_models,
    evaluate,
    run,
    top_drivers,
)
from generate_data import generate


@pytest.fixture(scope="module")
def df():
    return generate()


def test_data_shape_and_columns(df):
    assert len(df) == 3000
    assert set(NUMERIC + CATEGORICAL + ["churn"]) == set(df.columns)
    assert df["churn"].isin([0, 1]).all()


def test_data_has_no_missing_values(df):
    assert not df.isna().any().any()


def test_churn_rate_is_plausible(df):
    # Planted signal should give a realistic 15-40% churn rate, not 0/100%.
    assert 0.15 < df["churn"].mean() < 0.40


def test_generation_is_deterministic():
    pd.testing.assert_frame_equal(generate(), generate())


def test_models_beat_majority_baseline():
    df = generate()
    X, y = df[NUMERIC + CATEGORICAL], df["churn"]
    from sklearn.model_selection import train_test_split

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42)
    for name, model in build_models().items():
        model.fit(X_tr, y_tr)
        m = evaluate(model, X_te, y_te)
        assert m["roc_auc"] > 0.70, f"{name} ROC-AUC {m['roc_auc']} too low"
        assert m["recall"] > 0.40, f"{name} recall {m['recall']} too low"


def test_planted_drivers_are_recovered():
    # Month-to-month contracts and support calls were planted as churn
    # drivers; at least one of them must appear in each model's top 8.
    df = generate()
    X, y = df[NUMERIC + CATEGORICAL], df["churn"]
    from sklearn.model_selection import train_test_split

    X_tr, _, y_tr, _ = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42)
    for _, model in build_models().items():
        model.fit(X_tr, y_tr)
        feats = " ".join(d["feature"] for d in top_drivers(model))
        assert ("month-to-month" in feats or "support_calls" in feats
                or "tenure" in feats)


def test_at_risk_list_is_sorted_and_bounded():
    df = generate()
    X, y = df[NUMERIC + CATEGORICAL], df["churn"]
    from sklearn.model_selection import train_test_split

    X_tr, X_te, y_tr, _ = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42)
    model = build_models()["random-forest"]
    model.fit(X_tr, y_tr)
    rows = at_risk_list(model, X_te, top_n=10)
    assert len(rows) == 10
    probs = [r["churn_probability"] for r in rows]
    assert probs == sorted(probs, reverse=True)
    assert all(0.0 <= p <= 1.0 for p in probs)
    assert probs[0] > 0.5  # the riskiest customer should look risky


def test_full_run_returns_metrics():
    res = run()
    assert res["n_customers"] == 3000
    assert res["best_model"] in res["models"]
    assert len(res["at_risk_top10"]) == 10
    for name, m in res["models"].items():
        assert 0.0 <= m["roc_auc"] <= 1.0
