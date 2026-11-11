"""sktime time-series forecaster proof — AirPassengers.

Loads sktime's built-in AirPassengers series (monthly airline passengers,
1949-1960, 144 observations, source: Box & Jenkins via sktime.datasets),
fits three sktime forecasters, and evaluates them on the last 24 months
against a seasonal-naive baseline.

No affiliation with sktime. Small series, demonstration only.
"""

import json
from pathlib import Path

import pandas as pd
from sktime.datasets import load_airline
from sktime.forecasting.compose import make_reduction
from sktime.forecasting.exp_smoothing import ExponentialSmoothing
from sktime.forecasting.naive import NaiveForecaster
from sktime.performance_metrics.forecasting import mean_absolute_error, mean_squared_error
from sktime.split import temporal_train_test_split
from sklearn.ensemble import RandomForestRegressor

TEST_MONTHS = 24
SEASONAL_PERIOD = 12
RESULTS_PATH = Path(__file__).resolve().parent.parent / "results.json"


def load_series() -> pd.Series:
    """Load the AirPassengers series from sktime's built-in datasets."""
    y = load_airline()
    y = y.astype(float)
    return y


def build_forecasters():
    """Three sktime forecasters: seasonal naive, ETS, ML reduction."""
    return {
        "seasonal_naive": NaiveForecaster(strategy="last", sp=SEASONAL_PERIOD),
        # Fixed ETS(A,A,A): AutoETS auto-selection picked a poor model here
        # (MAE 115.25, worse than seasonal naive), so the additive
        # trend/seasonal ETS is specified explicitly.
        "ets": ExponentialSmoothing(
            trend="add", seasonal="add", sp=SEASONAL_PERIOD
        ),
        "random_forest_reduction": make_reduction(
            RandomForestRegressor(n_estimators=200, random_state=42),
            window_length=SEASONAL_PERIOD,
            strategy="recursive",
        ),
    }


def run() -> dict:
    y = load_series()
    y_train, y_test = temporal_train_test_split(y, test_size=TEST_MONTHS)
    fh = y_test.index

    results = {
        "dataset": "sktime.datasets.load_airline (AirPassengers, monthly, 1949-1960)",
        "n_observations": int(len(y)),
        "train_size": int(len(y_train)),
        "test_size": int(len(y_test)),
        "test_period": [str(fh[0]), str(fh[-1])],
        "models": {},
    }

    for name, forecaster in build_forecasters().items():
        forecaster.fit(y_train, fh=fh)
        y_pred = forecaster.predict(fh=fh)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(mean_squared_error(y_test, y_pred, square_root=True))
        results["models"][name] = {"mae": round(mae, 2), "rmse": round(rmse, 2)}
        print(f"{name:24s} MAE={mae:7.2f}  RMSE={rmse:7.2f}")

    baseline = results["models"]["seasonal_naive"]["mae"]
    for name, metrics in results["models"].items():
        metrics["mae_vs_seasonal_naive_pct"] = round(
            100.0 * (baseline - metrics["mae"]) / baseline, 1
        )
    best = min(results["models"], key=lambda k: results["models"][k]["mae"])
    results["best_model_by_mae"] = best
    print(f"Best by MAE: {best}")

    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    print(f"Wrote {RESULTS_PATH}")
    return results


if __name__ == "__main__":
    run()
