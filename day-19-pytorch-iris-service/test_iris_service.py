"""Tests for the Iris MLP service.

Run from the project folder (or anywhere) with:
    python -m pytest test_iris_service.py -v

The API tests train a throwaway model into a temp dir and point the
service at it via IRIS_MODEL_PATH / IRIS_METRICS_PATH, so they never
touch the real model.pt.
"""

import json
import os
from pathlib import Path

import pytest
import torch
from fastapi.testclient import TestClient

from model import CLASSES, IrisMLP
from train import load_data, stratified_split, train_model

HERE = Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    """Train once into a temp dir; return (model_path, metrics_path)."""
    tmp = tmp_path_factory.mktemp("iris")
    features, labels = load_data()
    model, mean, std, metrics = train_model(features, labels, epochs=100)
    model_path = tmp / "model.pt"
    metrics_path = tmp / "metrics.json"
    torch.save(
        {"state_dict": model.state_dict(), "hidden": model.hidden,
         "mean": mean, "std": std, "classes": CLASSES},
        model_path,
    )
    metrics_path.write_text(json.dumps(metrics))
    return model_path, metrics_path, metrics


@pytest.fixture(scope="module")
def client(trained):
    model_path, metrics_path, _ = trained
    old_model = os.environ.get("IRIS_MODEL_PATH")
    old_metrics = os.environ.get("IRIS_METRICS_PATH")
    os.environ["IRIS_MODEL_PATH"] = str(model_path)
    os.environ["IRIS_METRICS_PATH"] = str(metrics_path)
    import serve
    import importlib

    importlib.reload(serve)  # re-read env vars
    serve._model_cache.clear()
    yield TestClient(serve.app)
    if old_model is None:
        os.environ.pop("IRIS_MODEL_PATH", None)
    else:
        os.environ["IRIS_MODEL_PATH"] = old_model
    if old_metrics is None:
        os.environ.pop("IRIS_METRICS_PATH", None)
    else:
        os.environ["IRIS_METRICS_PATH"] = old_metrics


def test_data_loads_150_rows_balanced():
    features, labels = load_data()
    assert len(features) == 150 and len(labels) == 150
    assert all(len(f) == 4 for f in features)
    for cls in range(3):
        assert labels.count(cls) == 50


def test_split_is_stratified():
    features, labels = load_data()
    train_idx, val_idx, test_idx = stratified_split(features, labels, seed=42)
    assert len(train_idx) == 102 and len(val_idx) == 24 and len(test_idx) == 24
    for idx in (train_idx, val_idx, test_idx):
        counts = {c: sum(1 for i in idx if labels[i] == c) for c in range(3)}
        assert all(v >= 8 for v in counts.values())


def test_model_forward_shape():
    model = IrisMLP(hidden=16)
    out = model(torch.randn(5, 4))
    assert out.shape == (5, 3)


def test_training_reaches_high_accuracy(trained):
    _, _, metrics = trained
    assert metrics["test_accuracy"] >= 0.90
    assert metrics["val_accuracy"] >= 0.90


def test_api_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["trained"] is True


def test_api_predict_setosa(client):
    r = client.post("/predict", json={
        "sepal_length": 5.1, "sepal_width": 3.5,
        "petal_length": 1.4, "petal_width": 0.2})
    assert r.status_code == 200
    body = r.json()
    assert body["species"] == "setosa"
    assert abs(sum(body["probabilities"].values()) - 1.0) < 0.01
    assert set(body["probabilities"]) == set(CLASSES)


def test_api_predict_virginica(client):
    r = client.post("/predict", json={
        "sepal_length": 6.3, "sepal_width": 3.3,
        "petal_length": 6.0, "petal_width": 2.5})
    assert r.status_code == 200
    assert r.json()["species"] == "virginica"


def test_api_rejects_bad_input(client):
    r = client.post("/predict", json={"sepal_length": 5.1})
    assert r.status_code == 422
    r = client.post("/predict", json={
        "sepal_length": -1, "sepal_width": 3.5,
        "petal_length": 1.4, "petal_width": 0.2})
    assert r.status_code == 422


def test_api_metrics(client, trained):
    _, _, metrics = trained
    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.json()["test_accuracy"] == metrics["test_accuracy"]


def test_predict_cli():
    """The CLI predicts setosa for a classic setosa sample.

    Runs against the real model.pt, so it is skipped until train.py
    has been run once (CI trains first).
    """
    import subprocess
    import sys

    if not (HERE / "model.pt").exists():
        pytest.skip("real model.pt not trained yet — run python train.py")
    out = subprocess.run(
        [sys.executable, str(HERE / "predict.py"), "5.1", "3.5", "1.4", "0.2"],
        capture_output=True, text=True, cwd=HERE)
    assert out.returncode == 0
    assert "setosa" in out.stdout
