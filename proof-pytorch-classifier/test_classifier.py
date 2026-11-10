"""Tests for the PyTorch classifier.

Runs the full training pipeline end to end (small model, CPU, seconds)
and checks the measured test accuracy. No mocked results: the metric
reported here is the real one from the run.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import torch  # noqa: E402

import train  # noqa: E402

HERE = Path(__file__).parent


def test_training_produces_real_accuracy():
    metrics = train.main()
    assert metrics["test_size"] == 360
    assert metrics["test_accuracy"] >= 0.90, metrics
    saved = json.loads((HERE / "metrics.json").read_text())
    assert saved["test_accuracy"] == metrics["test_accuracy"]


def test_model_forward_shape():
    model = train.MLP()
    out = model(torch.zeros(5, 64))
    assert out.shape == (5, 10)


if __name__ == "__main__":
    test_training_produces_real_accuracy()
    test_model_forward_shape()
    print("All tests passed.")
