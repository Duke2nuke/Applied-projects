"""Task 1: convolutional autoencoder on 125x125x3 synthetic jet images.
Input transform: log1p (images are heavy-tailed), then per-channel
standardisation from the train split. Reports MSE overall + per channel
on train/val/test. Saves outputs/reconstruction.png (2 test jets x 3
channels, original vs reconstructed) and outputs/ae_metrics.json.
CPU, seed 42. Run: .venv/bin/python train_ae.py
"""
import json
import numpy as np
import torch
import torch.nn as nn
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from models import ConvAE

torch.manual_seed(42)
torch.set_num_threads(4)
DEVICE = "cpu"


def load():
    d = np.load("data/synth_jets.npz")
    x, y = np.log1p(d["x"].astype(np.float32)), d["y"]
    rng = np.random.default_rng(42)
    idx = rng.permutation(len(y))
    tr, va, te = idx[:800], idx[800:1000], idx[1000:]
    mu, sd = x[tr].mean(axis=(0, 2, 3), keepdims=True), x[tr].std(axis=(0, 2, 3), keepdims=True) + 1e-6
    return (torch.tensor((x[tr] - mu) / sd), torch.tensor((x[va] - mu) / sd),
            torch.tensor((x[te] - mu) / sd), y[te])


def mse_per_channel(model, x):
    model.eval()
    with torch.no_grad():
        recon = torch.cat([model(x[i:i + 64]) for i in range(0, len(x), 64)])
    err = ((recon - x) ** 2)
    return float(err.mean()), [float(err[:, c].mean()) for c in range(3)], recon


def main():
    xtr, xva, xte, yte = load()
    model = ConvAE()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()
    n_epochs, bs = 6, 16
    for ep in range(n_epochs):
        model.train()
        perm = torch.randperm(len(xtr))
        tot = 0.0
        for i in range(0, len(xtr), bs):
            b = xtr[perm[i:i + bs]]
            opt.zero_grad()
            loss = loss_fn(model(b), b)
            loss.backward()
            opt.step()
            tot += float(loss) * len(b)
        print(f"epoch {ep + 1}/{n_epochs} train MSE {tot / len(xtr):.4f}", flush=True)
    res = {}
    for name, xx in (("train", xtr), ("val", xva), ("test", xte)):
        m, per, _ = mse_per_channel(model, xx)
        res[name] = {"mse": m, "mse_per_channel": per}
        print(f"{name} MSE {m:.4f} per-channel {[round(v, 4) for v in per]}")
    torch.save(model.state_dict(), "outputs/ae.pt")
    # figure: 2 test jets (1 quark, 1 gluon) x 3 channels, orig vs recon
    _, _, recon = mse_per_channel(model, xte)
    fig, axes = plt.subplots(2, 6, figsize=(12, 4))
    for r, j in enumerate([0, 1]):
        for c in range(3):
            axes[r, 2 * c].imshow(xte[j, c], cmap="viridis")
            axes[r, 2 * c].set_title(f"jet{r} {'Tracks' if c == 0 else 'ECAL' if c == 1 else 'HCAL'} orig")
            axes[r, 2 * c + 1].imshow(recon[j, c], cmap="viridis")
            axes[r, 2 * c + 1].set_title("recon")
            axes[r, 2 * c].axis("off")
            axes[r, 2 * c + 1].axis("off")
    plt.tight_layout()
    plt.savefig("outputs/reconstruction.png", dpi=100)
    res["figure"] = "outputs/reconstruction.png"
    res["note"] = ("MSE is on log1p+standardised pixels, not raw energy. "
                   "Synthetic data: see README.md.")
    json.dump(res, open("outputs/ae_metrics.json", "w"), indent=2)
    print("saved outputs/ae_metrics.json + outputs/reconstruction.png")


if __name__ == "__main__":
    main()
