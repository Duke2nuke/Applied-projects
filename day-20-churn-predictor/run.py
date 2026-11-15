"""Entry point: generate data, train both models, print the report, save metrics."""

import json

from churn import print_report, run

if __name__ == "__main__":
    results = run()
    with open("metrics.json", "w") as f:
        json.dump(results, f, indent=2)
    print_report(results)
    print("\nWrote metrics.json")
