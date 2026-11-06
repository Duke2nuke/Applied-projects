"""CLI entry point: generate the synthetic series, walk-forward evaluate
the three models, and print a 7-day forecast.

Usage:
    python run.py            # full report + 7-day forecast
    python run.py --days 7   # forecast horizon in days
"""

import argparse

from forecast import (
    DAYS,
    forecast_next_days,
    generate_series,
    walk_forward,
)


def main():
    parser = argparse.ArgumentParser(description="Daily demand forecaster")
    parser.add_argument("--days", type=int, default=7,
                        help="forecast horizon in days (default 7)")
    args = parser.parse_args()

    series = generate_series()
    print(f"Daily demand forecaster — {DAYS} synthetic days "
          f"(campus canteen orders)")
    print(f"Series range: {min(series):.1f} to {max(series):.1f} "
          f"orders/day, mean {sum(series) / len(series):.1f}\n")

    print("Walk-forward evaluation (train on first 200 days, "
          "one-step-ahead on the last 165):")
    print(f"{'model':<10} {'MAE':>8} {'RMSE':>8}")
    results = walk_forward(series)
    for model in ("naive", "seasonal", "ridge"):
        m, r = results[model]
        print(f"{model:<10} {m:8.2f} {r:8.2f}")
    best = min(results, key=lambda m: results[m][0])
    print(f"\nBest by MAE: {best} "
          f"({results[best][0]:.2f} vs seasonal-naive "
          f"{results['seasonal'][0]:.2f})")

    print(f"\nNext {args.days}-day forecast (ridge, feeding predictions "
          "back in):")
    for i, pred in enumerate(forecast_next_days(series, args.days), 1):
        print(f"  day +{i}: {pred:6.1f} orders")


if __name__ == "__main__":
    main()
