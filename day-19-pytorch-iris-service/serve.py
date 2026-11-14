"""Serve the trained Iris MLP as a small FastAPI service.

Endpoints:
    GET  /health   -> {"status": "ok", ...} (200 even before training)
    POST /predict  -> {"species": ..., "probabilities": {...}}
    GET  /metrics  -> the train.py eval report (503 if not trained yet)

Model path can be overridden for tests via IRIS_MODEL_PATH and
IRIS_METRICS_PATH. Run with:
    uvicorn serve:app --reload
"""

import json
import os
from pathlib import Path

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from model import CLASSES, IrisMLP, predict_species

HERE = Path(__file__).resolve().parent
MODEL_PATH = Path(os.environ.get("IRIS_MODEL_PATH", HERE / "model.pt"))
METRICS_PATH = Path(os.environ.get("IRIS_METRICS_PATH", HERE / "metrics.json"))

app = FastAPI(title="Iris MLP service", version="1.0.0")

_model_cache = {}


class IrisInput(BaseModel):
    sepal_length: float = Field(..., gt=0, description="Sepal length in cm")
    sepal_width: float = Field(..., gt=0, description="Sepal width in cm")
    petal_length: float = Field(..., gt=0, description="Petal length in cm")
    petal_width: float = Field(..., gt=0, description="Petal width in cm")


def _load_model():
    if "model" not in _model_cache:
        if not MODEL_PATH.exists():
            return None
        ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        model = IrisMLP(hidden=ckpt["hidden"])
        model.load_state_dict(ckpt["state_dict"])
        _model_cache["model"] = model
        _model_cache["mean"] = ckpt["mean"]
        _model_cache["std"] = ckpt["std"]
    return _model_cache


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": "iris-mlp",
        "classes": CLASSES,
        "trained": MODEL_PATH.exists(),
    }


@app.post("/predict")
def predict(inp: IrisInput):
    loaded = _load_model()
    if loaded is None:
        raise HTTPException(status_code=503, detail="model not trained yet — run python train.py")
    features = [inp.sepal_length, inp.sepal_width, inp.petal_length, inp.petal_width]
    species, probs = predict_species(loaded["model"], features, loaded["mean"], loaded["std"])
    return {"species": species, "probabilities": probs}


@app.get("/metrics")
def metrics():
    if not METRICS_PATH.exists():
        raise HTTPException(status_code=503, detail="no metrics yet — run python train.py")
    return json.loads(METRICS_PATH.read_text())
