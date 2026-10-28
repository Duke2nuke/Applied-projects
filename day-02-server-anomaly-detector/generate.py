"""Generate SYNTHETIC server-metrics data with labelled anomalies.

This is demo data, not real production telemetry. The point of the
project is the detector, not the data: a clean, labelled series lets
us measure precision/recall honestly instead of eyeballing a chart.

Series: hourly metrics for 14 days (336 points).
Features: cpu_percent, memory_percent, latency_ms, requests_per_min.
Normal behaviour: a daily cycle plus noise.
Injected anomalies (after the detector's 72-hour warm-up window, so
it has same-hour history to compare against): CPU spikes, latency
spikes, memory spikes, and request-rate collapses.
"""

import numpy as np
import pandas as pd

N_POINTS = 336  # 14 days, hourly
SEED = 42

# (index, feature, injected value, description)
ANOMALIES = [
    (84, "cpu_percent", 98.0, "CPU spike"),
    (95, "latency_ms", 950.0, "Latency spike"),
    (105, "requests_per_min", 40.0, "Request collapse"),
    (130, "cpu_percent", 97.0, "CPU spike"),
    (168, "memory_percent", 99.0, "Memory spike"),
    (195, "latency_ms", 1100.0, "Latency spike"),
    (222, "requests_per_min", 25.0, "Request collapse"),
    (260, "cpu_percent", 99.0, "CPU spike"),
    (288, "latency_ms", 880.0, "Latency spike"),
    (315, "memory_percent", 98.0, "Memory spike"),
]


def generate(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(N_POINTS)
    daily = np.sin(2 * np.pi * t / 24)  # daily cycle, peak mid-day

    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-10-01", periods=N_POINTS, freq="h"),
            "cpu_percent": np.clip(48 + 14 * daily + rng.normal(0, 4, N_POINTS), 0, 100),
            "memory_percent": np.clip(58 + 6 * daily + rng.normal(0, 3, N_POINTS), 0, 100),
            "latency_ms": np.clip(120 + 35 * daily + rng.normal(0, 18, N_POINTS), 1, None),
            "requests_per_min": np.clip(820 + 260 * daily + rng.normal(0, 90, N_POINTS), 0, None),
            "is_anomaly": False,
        }
    )
    for idx, feature, value, _ in ANOMALIES:
        df.loc[idx, feature] = value
        df.loc[idx, "is_anomaly"] = True
    return df


if __name__ == "__main__":
    data = generate()
    data.to_csv("metrics.csv", index=False)
    print(f"Wrote metrics.csv: {len(data)} rows, {data['is_anomaly'].sum()} labelled anomalies")
