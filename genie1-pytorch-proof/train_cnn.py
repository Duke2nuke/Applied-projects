"""CNN image baseline for quark/gluon on the synthetic 125x125x3 images.
Same split/transform as train_ae.py (stratified 800/200/200, seed 42).
Reports accuracy, precision, recall, F1, ROC-AUC + confusion matrix on
the held-out test set. Saves outputs/cnn_metrics.json.
Run: .venv/bin/python train_cnn.py
"""
import json
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, confusion_matrix)
from models import CNNClassifier

torch.manual_seed(42)
torch.set_num_threads(4)


def load():
    d = np.load("data/synth_jets.npz")
    x, y = np.log1p(d["x"].astype(np.float32)), d["y"]
    rng = np.random.default_rng(42)
    idx = rng.permutation(len(y))
    tr, va, te = idx[:800], idx[800:1000], idx[1000:]
    mu, sd = x[tr].mean(axis=(0, 2, 3), keepdims=True), x[tr].std(axis=(0, 2, 3), keepdims=True) + 1e-6
    return (torch.tensor((x[tr] - mu) / sd), y[tr],
            torch.tensor((x[va] - mu) / sd), y[va],
            torch.tensor((x[te] - mu) / sd), y[te])


def predict(model, x):
    model.eval()
    with torch.no_grad():
        logits = torch.cat([model(x[i:i + 64]) for i in range(0, len(x), 64)])
    return torch.softmax(logits, 1).numpy()


def main():
    xtr, ytr, xva, yva, xte, yte = load()
    model = CNNClassifier()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.CrossEntropyLoss()
    for ep in range(8):
        model.train()
        perm = torch.randperm(len(xtr))
        tot = 0.0
        for i in range(0, len(xtr), 32):
            j = perm[i:i + 32]
            opt.zero_grad()
            loss = loss_fn(model(xtr[j]), torch.tensor(ytr[j]))
            loss.backward()
            opt.step()
            tot += float(loss) * len(j)
        va = predict(model, xva).argmax(1)
        print(f"epoch {ep + 1}/8 train loss {tot / len(xtr):.4f} "
              f"val acc {accuracy_score(yva, va):.4f}", flush=True)
    p = predict(model, xte)
    pred = p.argmax(1)
    res = {
        "n_train": 800, "n_val": 200, "n_test": 200, "seed": 42,
        "accuracy": float(accuracy_score(yte, pred)),
        "precision": float(precision_score(yte, pred)),
        "recall": float(recall_score(yte, pred)),
        "f1": float(f1_score(yte, pred)),
        "roc_auc": float(roc_auc_score(yte, p[:, 1])),
        "confusion_matrix": confusion_matrix(yte, pred).tolist(),
    }
    print(json.dumps(res, indent=2))
    json.dump(res, open("outputs/cnn_metrics.json", "w"), indent=2)
    torch.save(model.state_dict(), "outputs/cnn.pt")


if __name__ == "__main__":
    main()
