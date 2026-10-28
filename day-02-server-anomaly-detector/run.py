"""End-to-end demo: generate synthetic metrics, detect, report metrics.

Usage:
    python run.py
"""

from detector import FEATURES, detect, evaluate
from generate import ANOMALIES, generate


def main() -> None:
    df = generate()
    result = detect(df)
    metrics = evaluate(result)

    print(f"Rows: {len(df)} | Labelled anomalies: {int(df['is_anomaly'].sum())}")
    print(f"Metrics: {metrics}")
    print("\nTop 12 most anomalous points (by max |modified z|):")
    top = result.nlargest(12, "max_abs_z")
    for _, row in top.iterrows():
        worst = max(FEATURES, key=lambda f: abs(row[f"{f}_z"]))
        print(
            f"  {row['timestamp']}  {worst}={row[worst]:.1f}  "
            f"max|z|={row['max_abs_z']:.1f}  "
            f"labelled={'YES' if row['is_anomaly'] else 'no'}"
        )
    missed = result[result["is_anomaly"] & ~result["predicted_anomaly"]]
    if len(missed):
        print(f"\nMissed labelled anomalies: {len(missed)}")
        for _, row in missed.iterrows():
            print(f"  {row['timestamp']}  max|z|={row['max_abs_z']:.1f}")
    else:
        print("\nMissed labelled anomalies: 0")
    print(f"\nInjected anomaly types: {sorted({d for _, _, _, d in ANOMALIES})}")


if __name__ == "__main__":
    main()
