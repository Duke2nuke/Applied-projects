"""Tests for the data-science SQL pipeline.

Rebuilds the database from scratch, runs the full analysis, and checks the
real measured metric. No mocked results.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import analysis  # noqa: E402
import create_db  # noqa: E402

HERE = Path(__file__).parent


def test_full_pipeline():
    counts = create_db.main()
    assert counts == {"customers": 40, "products": 12, "orders": 300}
    metrics = analysis.main()
    assert metrics["n_orders"] == 300
    assert metrics["missing_values"] == 0
    assert metrics["test_size"] == 60
    assert metrics["rmse"] < 40.0, metrics
    assert metrics["r2"] > 0.85, metrics
    assert (HERE / "chart.svg").exists()
    assert (HERE / "metrics.json").exists()
    saved = json.loads((HERE / "metrics.json").read_text())
    assert saved["rmse"] == metrics["rmse"]


if __name__ == "__main__":
    test_full_pipeline()
    print("All tests passed.")
