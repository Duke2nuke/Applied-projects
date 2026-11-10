"""Train + evaluate seva-triage, print metrics, write metrics.json."""

import json

from model import evaluate


def main():
    metrics, report = evaluate()
    print(f"total: {metrics['n_total']}  train: {metrics['n_train']}  test: {metrics['n_test']}")
    print(f"accuracy: {metrics['accuracy']}")
    print(f"macro F1: {metrics['macro_f1']}")
    print(f"department counts: {metrics['department_counts']}")
    print()
    print(report)
    with open("metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print("wrote metrics.json")


if __name__ == "__main__":
    main()
