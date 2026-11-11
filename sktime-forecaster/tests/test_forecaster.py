"""Tests for the sktime forecaster proof.

Covers: data loading, forecaster fitting/prediction, evaluation metrics.
Run: .venv/bin/python -m pytest tests/ -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from forecast import build_forecasters, load_series, run  # noqa: E402
from sktime.performance_metrics.forecasting import mean_absolute_error  # noqa: E402
from sktime.split import temporal_train_test_split  # noqa: E402


def test_data_loads():
    y = load_series()
    assert isinstance(y, pd.Series)
    assert len(y) == 144, f"expected 144 monthly observations, got {len(y)}"
    assert y.isna().sum() == 0
    assert (y > 0).all()
    assert str(y.index[0]).startswith("1949")
    assert str(y.index[-1]).startswith("1960")


def test_forecasters_fit_and_predict():
    y = load_series()
    y_train, y_test = temporal_train_test_split(y, test_size=24)
    fh = y_test.index
    for name, forecaster in build_forecasters().items():
        forecaster.fit(y_train, fh=fh)
        y_pred = forecaster.predict(fh=fh)
        assert len(y_pred) == 24, f"{name}: expected 24 predictions"
        assert np.isfinite(y_pred.values).all(), f"{name}: non-finite predictions"
        assert (y_pred.values > 0).all(), f"{name}: non-positive predictions"


def test_evaluation_metrics_are_sane():
    y = load_series()
    y_train, y_test = temporal_train_test_split(y, test_size=24)
    fh = y_test.index
    maes = {}
    for name, forecaster in build_forecasters().items():
        forecaster.fit(y_train, fh=fh)
        maes[name] = mean_absolute_error(y_test, forecaster.predict(fh=fh))
    # Every model must beat a trivial zero forecast and be within a sane band.
    for name, mae in maes.items():
        assert 0 < mae < 200, f"{name}: implausible MAE {mae}"
    # The ML and ETS models should beat the seasonal-naive baseline here;
    # at minimum they must not be catastrophically worse than it.
    assert maes["ets"] < 2 * maes["seasonal_naive"]
    assert maes["random_forest_reduction"] < 2 * maes["seasonal_naive"]


def test_run_writes_results(tmp_path, monkeypatch):
    import forecast

    results_path = tmp_path / "results.json"
    monkeypatch.setattr(forecast, "RESULTS_PATH", results_path)
    results = run()
    assert results_path.exists()
    assert set(results["models"]) == {
        "seasonal_naive",
        "ets",
        "random_forest_reduction",
    }
    assert results["test_size"] == 24
    assert results["best_model_by_mae"] in results["models"]
