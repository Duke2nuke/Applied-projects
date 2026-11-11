"""Tests for the scikit-learn evaluation classifier proof project.

Run:  .venv/bin/python -m pytest test_sklearn_eval.py -v
Covers: data loading, stratified split, training of both models,
reproducible evaluation metrics, and the metrics.json output.
"""

import json
from pathlib import Path

import numpy as np
import pytest
from sklearn.model_selection import train_test_split

import sklearn_eval as se

HERE = Path(__file__).resolve().parent


def test_data_loads_real_dataset():
    X, y, target_names = se.load_data()
    assert X.shape == (569, 30)
    assert y.shape == (569,)
    assert target_names == ["malignant", "benign"]
    assert set(np.unique(y)) == {0, 1}


def test_split_is_stratified():
    X, y, _ = se.load_data()
    _, _, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=se.RANDOM_STATE, stratify=y
    )
    # Both classes present in both splits, in roughly the dataset ratio.
    assert len(y_train) == 455
    assert len(y_test) == 114
    for split in (y_train, y_test):
        assert set(np.unique(split)) == {0, 1}
        assert 0.60 < float(np.mean(split)) < 0.65  # benign share ~0.627


def test_both_models_train_and_predict():
    X, y, _ = se.load_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=se.RANDOM_STATE, stratify=y
    )
    for name, model in se.make_models().items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        assert len(pred) == 114
        assert set(np.unique(pred)).issubset({0, 1})
        # Sanity: both models must beat a majority-class baseline (~0.63).
        assert float(np.mean(pred == y_test)) > 0.90, name


def test_evaluation_metrics_reproducible_and_in_range():
    X, y, target_names = se.load_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=se.RANDOM_STATE, stratify=y
    )
    for name, model in se.make_models().items():
        m1 = se.evaluate_model(model, X_train, X_test, y_train, y_test, target_names)
        m2 = se.evaluate_model(
            se.make_models()[name], X_train, X_test, y_train, y_test, target_names
        )
        assert m1["test_accuracy"] == m2["test_accuracy"], name
        assert m1["test_f1_macro"] == m2["test_f1_macro"], name
        assert m1["confusion_matrix"] == m2["confusion_matrix"], name
        for key in (
            "test_accuracy",
            "test_precision_macro",
            "test_recall_macro",
            "test_f1_macro",
            "cv_accuracy_mean",
            "cv_f1_macro_mean",
        ):
            assert 0.0 <= m1[key] <= 1.0, (name, key)
        cm = np.array(m1["confusion_matrix"])
        assert cm.shape == (2, 2)
        assert int(cm.sum()) == 114
        assert "malignant" in m1["classification_report"]
        assert "benign" in m1["classification_report"]


def test_main_writes_metrics_json():
    results = se.main()
    path = HERE / "metrics.json"
    assert path.exists()
    saved = json.loads(path.read_text())
    assert saved["dataset"] == "sklearn.datasets.load_breast_cancer"
    assert saved["n_samples"] == 569
    assert set(saved["models"]) == {"logistic_regression", "random_forest"}
    for name in ("logistic_regression", "random_forest"):
        assert saved["models"][name]["test_accuracy"] == results["models"][name][
            "test_accuracy"
        ]
