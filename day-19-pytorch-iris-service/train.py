"""Train the PyTorch Iris MLP and write model.pt + metrics.json.

Data: the classic Fisher Iris dataset (150 rows, bundled as iris.csv,
source: UCI Machine Learning Repository). Split is stratified and
seeded (seed 42): 70% train / 15% validation / 15% test, per class.
Features are standardised with the train-set mean and std.

Usage:
    python train.py [--epochs 200] [--lr 0.01] [--seed 42]
"""

import argparse
import csv
import json
import random
from pathlib import Path

import torch
import torch.nn as nn

from model import CLASSES, IrisMLP

HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / "iris.csv"
MODEL_PATH = HERE / "model.pt"
METRICS_PATH = HERE / "metrics.json"


def load_data(path=DATA_PATH):
    """Return (features, labels) as lists: 150 rows, 4 floats + class index."""
    features, labels = [], []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            features.append(
                [
                    float(row["sepal_length"]),
                    float(row["sepal_width"]),
                    float(row["petal_length"]),
                    float(row["petal_width"]),
                ]
            )
            labels.append(CLASSES.index(row["species"]))
    return features, labels


def stratified_split(features, labels, seed=42):
    """Seeded stratified split: 70% train / 15% val / 15% test per class."""
    rng = random.Random(seed)
    train_idx, val_idx, test_idx = [], [], []
    for cls in range(len(CLASSES)):
        idx = [i for i, y in enumerate(labels) if y == cls]
        rng.shuffle(idx)
        n = len(idx)
        n_test = round(n * 0.15)
        n_val = round(n * 0.15)
        test_idx += idx[:n_test]
        val_idx += idx[n_test : n_test + n_val]
        train_idx += idx[n_test + n_val :]
    return train_idx, val_idx, test_idx


def train_model(features, labels, epochs=200, lr=0.01, seed=42, hidden=16):
    """Train on the train split; return (model, mean, std, metrics dict)."""
    torch.manual_seed(seed)
    train_idx, val_idx, test_idx = stratified_split(features, labels, seed)

    x = torch.tensor(features, dtype=torch.float32)
    y = torch.tensor(labels, dtype=torch.long)
    mean = x[train_idx].mean(dim=0)
    std = x[train_idx].std(dim=0)
    x = (x - mean) / std

    model = IrisMLP(hidden=hidden)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss()

    for _ in range(epochs):
        model.train()
        opt.zero_grad()
        loss = loss_fn(model(x[train_idx]), y[train_idx])
        loss.backward()
        opt.step()

    def accuracy(idx):
        model.eval()
        with torch.no_grad():
            pred = model(x[idx]).argmax(dim=1)
        return float((pred == y[idx]).float().mean())

    per_class = {}
    model.eval()
    with torch.no_grad():
        pred = model(x[test_idx]).argmax(dim=1)
        final_loss = float(loss_fn(model(x[train_idx]), y[train_idx]))
    for cls, name in enumerate(CLASSES):
        mask = [i for i, j in enumerate(test_idx) if labels[j] == cls]
        correct = sum(1 for i in mask if int(pred[i]) == cls)
        per_class[name] = round(correct / len(mask), 4) if mask else None

    metrics = {
        "epochs": epochs,
        "learning_rate": lr,
        "seed": seed,
        "hidden_units": hidden,
        "split": {"train": len(train_idx), "val": len(val_idx), "test": len(test_idx)},
        "train_accuracy": round(accuracy(train_idx), 4),
        "val_accuracy": round(accuracy(val_idx), 4),
        "test_accuracy": round(accuracy(test_idx), 4),
        "test_accuracy_per_class": per_class,
        "final_train_loss": round(final_loss, 4),
    }
    return model, mean.tolist(), std.tolist(), metrics


def main():
    parser = argparse.ArgumentParser(description="Train the Iris MLP.")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    features, labels = load_data()
    model, mean, std, metrics = train_model(
        features, labels, epochs=args.epochs, lr=args.lr, seed=args.seed
    )
    torch.save(
        {
            "state_dict": model.state_dict(),
            "hidden": model.hidden,
            "mean": mean,
            "std": std,
            "classes": CLASSES,
        },
        MODEL_PATH,
    )
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n")
    print(f"trained on {metrics['split']['train']} rows, "
          f"val {metrics['split']['val']}, test {metrics['split']['test']}")
    print(f"train acc {metrics['train_accuracy']:.4f} | "
          f"val acc {metrics['val_accuracy']:.4f} | "
          f"test acc {metrics['test_accuracy']:.4f}")
    print(f"per-class test acc: {metrics['test_accuracy_per_class']}")
    print(f"wrote {MODEL_PATH.name} and {METRICS_PATH.name}")


if __name__ == "__main__":
    main()
