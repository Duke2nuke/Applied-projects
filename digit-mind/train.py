"""PyTorch classifier on the sklearn Digits dataset (1797 small 8x8 images).

Real training, CPU-only, fixed seed. Trains a small MLP (64 -> 32 -> 10)
and reports held-out test accuracy. No synthetic labels: the dataset is the
public sklearn Digits dataset (handwritten digits, 8x8 pixels).
"""

import json
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split

SEED = 42
EPOCHS = 30
BATCH = 64
LR = 0.01
HERE = Path(__file__).parent


class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 10),
        )

    def forward(self, x):
        return self.net(x)


def main():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    digits = load_digits()
    X = digits.data.astype(np.float32) / 16.0  # pixel values 0-16
    y = digits.target.astype(np.int64)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )
    X_train_t = torch.from_numpy(X_train)
    y_train_t = torch.from_numpy(y_train)
    X_test_t = torch.from_numpy(X_test)
    y_test_t = torch.from_numpy(y_test)

    model = MLP()
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.CrossEntropyLoss()

    for epoch in range(EPOCHS):
        model.train()
        perm = torch.randperm(len(X_train_t))
        for i in range(0, len(perm), BATCH):
            idx = perm[i : i + BATCH]
            opt.zero_grad()
            out = model(X_train_t[idx])
            loss = loss_fn(out, y_train_t[idx])
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        preds = model(X_test_t).argmax(dim=1)
        acc = (preds == y_test_t).float().mean().item()

    torch.save(model.state_dict(), HERE / "model.pt")
    metrics = {
        "dataset": "sklearn Digits (1797 8x8 images, 10 classes)",
        "train_size": len(X_train_t),
        "test_size": len(X_test_t),
        "epochs": EPOCHS,
        "test_accuracy": round(acc, 4),
    }
    (HERE / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"Test accuracy: {acc:.4f} ({len(X_test_t)} held-out images)")
    return metrics


if __name__ == "__main__":
    main()
