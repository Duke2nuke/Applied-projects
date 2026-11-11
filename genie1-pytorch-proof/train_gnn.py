"""Task 2: GNN quark/gluon classifier on REAL JetNet point clouds.
Nodes = particles (<=30/jet, features eta/phi/log-pt/mask), edges = k=8
nearest neighbours in (eta, phi). Mean-aggregation message passing,
pure PyTorch (no PyTorch Geometric). Stratified 2800/600/600, seed 42.
Reports accuracy, precision, recall, F1, ROC-AUC + confusion matrix on
the held-out test set. Saves outputs/gnn_metrics.json.
Run: .venv/bin/python train_gnn.py
"""
import json
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, confusion_matrix)
from models import GNNClassifier

torch.manual_seed(42)
torch.set_num_threads(4)


def load():
    d = np.load("data/jetnet_graphs.npz")
    feat, edges, mask, y = d["feat"], d["edges"], d["mask"], d["y"]
    rng = np.random.default_rng(42)
    idx = rng.permutation(len(y))
    tr, va, te = idx[:2800], idx[2800:3400], idx[3400:]
    t = lambda a, i: torch.tensor(a[i])
    return (t(feat, tr), t(edges, tr), t(mask, tr), y[tr],
            t(feat, va), t(edges, va), t(mask, va), y[va],
            t(feat, te), t(edges, te), t(mask, te), y[te])


def predict(model, f, e, m):
    model.eval()
    with torch.no_grad():
        logits = torch.cat([model(f[i:i + 128], e[i:i + 128], m[i:i + 128])
                            for i in range(0, len(f), 128)])
    return torch.softmax(logits, 1).numpy()


def main():
    ftr, etr, mtr, ytr, fva, eva, mva, yva, fte, ete, mte, yte = load()
    model = GNNClassifier()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.CrossEntropyLoss()
    for ep in range(8):
        model.train()
        perm = torch.randperm(len(ftr))
        tot = 0.0
        for i in range(0, len(ftr), 32):
            j = perm[i:i + 32]
            opt.zero_grad()
            loss = loss_fn(model(ftr[j], etr[j], mtr[j]), torch.tensor(ytr[j]))
            loss.backward()
            opt.step()
            tot += float(loss) * len(j)
        va = predict(model, fva, eva, mva).argmax(1)
        print(f"epoch {ep + 1}/8 train loss {tot / len(ftr):.4f} "
              f"val acc {accuracy_score(yva, va):.4f}", flush=True)
    p = predict(model, fte, ete, mte)
    pred = p.argmax(1)
    res = {
        "n_train": 2800, "n_val": 600, "n_test": 600, "seed": 42,
        "accuracy": float(accuracy_score(yte, pred)),
        "precision": float(precision_score(yte, pred)),
        "recall": float(recall_score(yte, pred)),
        "f1": float(f1_score(yte, pred)),
        "roc_auc": float(roc_auc_score(yte, p[:, 1])),
        "confusion_matrix": confusion_matrix(yte, pred).tolist(),
    }
    print(json.dumps(res, indent=2))
    json.dump(res, open("outputs/gnn_metrics.json", "w"), indent=2)
    torch.save(model.state_dict(), "outputs/gnn.pt")


if __name__ == "__main__":
    main()
