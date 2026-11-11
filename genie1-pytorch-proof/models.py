"""Models for the GENIE1 local proof pipeline (pure PyTorch, CPU).

ConvAE        : Task 1 autoencoder on 125x125x3 jet images.
CNNClassifier : image baseline for quark/gluon on the same images.
GraphEncoder  : mean-aggregation message passing (GraphSAGE-style) on
                JetNet point clouds; pure PyTorch, NO PyTorch Geometric
                (kept out deliberately: pyg CPU wheels are fragile and
                the 30-node graphs do not need it). Edges are precomputed
                k=8 nearest neighbours in (eta, phi).
GNNClassifier : GraphEncoder + MLP head (Task 2 baseline).
Contrastive   : GraphEncoder + projection head, NT-Xent (Specific Task 1).
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class ConvAE(nn.Module):
    def __init__(self, latent=128):
        super().__init__()
        self.enc = nn.Sequential(
            nn.Conv2d(3, 16, 4, 2, 1), nn.ReLU(),   # 125 -> 63
            nn.Conv2d(16, 32, 4, 2, 1), nn.ReLU(),  # 63 -> 32
            nn.Conv2d(32, 64, 4, 2, 1), nn.ReLU(),  # 32 -> 16
        )
        # 125 -> 62 -> 31 -> 15 (k=4, s=2, p=1)
        self.fc1 = nn.Linear(64 * 15 * 15, latent)
        self.fc2 = nn.Linear(latent, 64 * 15 * 15)
        self.dec = nn.Sequential(
            nn.ConvTranspose2d(64, 32, 4, 2, 1), nn.ReLU(),  # 15 -> 30
            nn.ConvTranspose2d(32, 16, 4, 2, 1), nn.ReLU(),  # 30 -> 60
            nn.ConvTranspose2d(16, 3, 7, 2, 0),              # 60 -> 125
        )

    def forward(self, x):
        z = self.fc1(self.enc(x).flatten(1))
        return self.dec(self.fc2(z).view(-1, 64, 15, 15))


class CNNClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, 1, 1), nn.ReLU(), nn.MaxPool2d(2),  # 125->62
            nn.Conv2d(16, 32, 3, 1, 1), nn.ReLU(), nn.MaxPool2d(2),  # 62->31
            nn.Conv2d(32, 64, 3, 1, 1), nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.head = nn.Linear(64, 2)

    def forward(self, x):
        return self.head(self.features(x).flatten(1))


class GraphEncoder(nn.Module):
    """2 message-passing layers; neighbour mean over kNN edges + self."""

    def __init__(self, in_dim=4, hid=64):
        super().__init__()
        self.lin1 = nn.Linear(in_dim, hid)
        self.lin2 = nn.Linear(hid, hid)

    def _layer(self, h, edges, mask, lin):
        # h: (B, N, D); edges: (B, N, K) neighbour indices
        B, N, D = h.shape
        flat = h.reshape(B * N, D)
        off = (torch.arange(B, device=h.device) * N).view(B, 1, 1)
        neigh = flat[(edges + off).reshape(-1)].view(B, N, -1, D)
        agg = neigh.mean(dim=2)                       # (B, N, D)
        return F.relu(lin(0.5 * h + 0.5 * agg)) * mask.unsqueeze(-1)

    def forward(self, feat, edges, mask):
        h = self._layer(feat, edges, mask, self.lin1)
        h = self._layer(h, edges, mask, self.lin2)
        pooled = (h * mask.unsqueeze(-1)).sum(1) / mask.sum(1, keepdim=True)
        return pooled  # (B, hid)


class GNNClassifier(nn.Module):
    def __init__(self, hid=64):
        super().__init__()
        self.enc = GraphEncoder(hid=hid)
        self.head = nn.Sequential(nn.Linear(hid, 32), nn.ReLU(), nn.Linear(32, 2))

    def forward(self, feat, edges, mask):
        return self.head(self.enc(feat, edges, mask))


class ContrastiveModel(nn.Module):
    def __init__(self, hid=64, proj=32):
        super().__init__()
        self.enc = GraphEncoder(hid=hid)
        self.proj = nn.Sequential(nn.Linear(hid, proj), nn.ReLU(), nn.Linear(proj, proj))

    def forward(self, feat, edges, mask):
        return F.normalize(self.proj(self.enc(feat, edges, mask)), dim=1)
