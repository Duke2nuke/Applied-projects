"""Specific Task 1: contrastive representation + linear probe, JetNet graphs.
Encoder = same GraphEncoder as the Task 2 GNN baseline. Two views of each
graph = random node dropout (p=0.2, features zeroed, edges kept); NT-Xent
loss, temperature 0.2 (GLADC value). Then the encoder is FROZEN and a
logistic-regression linear probe is trained on the 64-d embeddings.
Reported on the SAME 2800/600/600 split as train_gnn.py so the probe
ROC-AUC is directly comparable to the GNN baseline. Saves
outputs/contrastive_metrics.json. Run: .venv/bin/python train_contrastive.py
"""
import json
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, confusion_matrix)
from models import ContrastiveModel

torch.manual_seed(42)
torch.set_num_threads(4)
TAU = 0.2


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


def drop_nodes(feat, mask, p=0.2):
    keep = (torch.rand_like(mask) > p).float() * mask
    return feat * keep.unsqueeze(-1), keep


def nt_xent(z1, z2, tau=TAU):
    z = torch.cat([z1, z2])
    sim = z @ z.T / tau
    n = z1.size(0)
    labels = torch.cat([torch.arange(n, 2 * n), torch.arange(n)])
    sim = sim - torch.eye(2 * n) * 1e9
    return F.cross_entropy(sim, labels)


def embed(model, f, e, m):
    model.eval()
    with torch.no_grad():
        return torch.cat([model.enc(f[i:i + 128], e[i:i + 128], m[i:i + 128])
                          for i in range(0, len(f), 128)]).numpy()


def main():
    ftr, etr, mtr, ytr, fva, eva, mva, yva, fte, ete, mte, yte = load()
    model = ContrastiveModel()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    for ep in range(6):
        model.train()
        perm = torch.randperm(len(ftr))
        tot = 0.0
        for i in range(0, len(ftr), 64):
            j = perm[i:i + 64]
            f1, k1 = drop_nodes(ftr[j], mtr[j])
            f2, k2 = drop_nodes(ftr[j], mtr[j])
            opt.zero_grad()
            loss = nt_xent(model(f1, etr[j], k1), model(f2, etr[j], k2))
            loss.backward()
            opt.step()
            tot += float(loss) * len(j)
        print(f"epoch {ep + 1}/6 contrastive loss {tot / len(ftr):.4f}", flush=True)
    torch.save(model.state_dict(), "outputs/contrastive.pt")
    etr_e, eva_e, ete_e = embed(model, ftr, etr, mtr), embed(model, fva, eva, mva), embed(model, fte, ete, mte)
    probe = LogisticRegression(max_iter=1000, C=1.0).fit(etr_e, ytr)
    print(f"probe val acc {probe.score(eva_e, yva):.4f}")
    p = probe.predict_proba(ete_e)[:, 1]
    pred = (p > 0.5).astype(int)
    res = {
        "n_train": 2800, "n_val": 600, "n_test": 600, "seed": 42,
        "method": "NT-Xent tau=0.2, node-dropout views p=0.2, frozen encoder + logistic probe",
        "accuracy": float(accuracy_score(yte, pred)),
        "precision": float(precision_score(yte, pred)),
        "recall": float(recall_score(yte, pred)),
        "f1": float(f1_score(yte, pred)),
        "roc_auc": float(roc_auc_score(yte, p)),
        "confusion_matrix": confusion_matrix(yte, pred).tolist(),
    }
    print(json.dumps(res, indent=2))
    json.dump(res, open("outputs/contrastive_metrics.json", "w"), indent=2)


if __name__ == "__main__":
    main()
