"""Real JetNet quark/gluon point clouds -> kNN graphs (GENIE1 Task 2 input).

Source (verified 11 Nov 2026, Zenodo API): JetNet v2, record 6975118,
CC-BY 4.0, Kansal et al. arXiv:2106.11535.
  q.hdf5 (84,658,832 B, 170,679 jets) and g.hdf5 (87,919,040 B, 177,252 jets)
  direct links: https://zenodo.org/api/records/6975118/files/{q,g}.hdf5/content
Each jet: particle_features (30, 4) = [eta_rel, phi_rel, pt_rel, mask].
This is REAL simulated jet data, but NOT the GENIE1 test data: JetNet jets
are ~1 TeV point clouds, while the GENIE1 test uses 125x125x3 CMS images
(Andrews et al.), which has no direct free download. Graphs built here
(nodes = particles, edges = k=8 nearest neighbours in (eta, phi))
follow the test doc's Task 2 recipe.
"""
import h5py
import numpy as np

K = 8
SEED = 42


def knn_edges(eta_phi, k=K):
    """eta_phi: (N, 30, 2). Returns neighbour indices (N, 30, k), self excluded."""
    diff = eta_phi[:, :, None, :] - eta_phi[:, None, :, :]
    d2 = (diff * diff).sum(-1)
    d2 = d2 + np.eye(d2.shape[1], dtype=d2.dtype)[None] * 1e6
    return np.argsort(d2, axis=2)[:, :, :k].astype(np.int64)


def main(n_per_class=2000, out="data/jetnet_graphs.npz"):
    rng = np.random.default_rng(SEED)
    xs, ys = [], []
    for label, path in ((0, "data/q.hdf5"), (1, "data/g.hdf5")):
        with h5py.File(path, "r") as h:
            pf = h["particle_features"][:n_per_class].astype(np.float32)
        xs.append(pf)
        ys.append(np.full(n_per_class, label, dtype=np.int64))
    x = np.concatenate(xs)          # (N, 30, 4): eta, phi, pt_rel, mask
    y = np.concatenate(ys)
    idx = rng.permutation(len(y))
    x, y = x[idx], y[idx]
    edges = knn_edges(x[:, :, :2])
    # log pt as a node feature (pt_rel is heavy-tailed)
    feat = np.stack([x[:, :, 0], x[:, :, 1], np.log1p(x[:, :, 2] * 10),
                     x[:, :, 3]], axis=-1).astype(np.float32)
    np.savez_compressed(out, feat=feat, mask=x[:, :, 3], edges=edges, y=y)
    print(f"saved {out}: feat={feat.shape} edges={edges.shape} "
          f"quark={int((y==0).sum())} gluon={int((y==1).sum())} "
          f"mean_particles_per_jet={float(x[:, :, 3].sum(1).mean()):.1f}")
    for lab in (0, 1):
        m = y == lab
        print(f"  label {lab}: mean particles/jet "
              f"{float(x[m][:, :, 3].sum(1).mean()):.2f}, "
              f"mean |eta| {float(np.abs(x[m][:, :, 0]).mean()):.3f}")


if __name__ == "__main__":
    main()
