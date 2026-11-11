"""Synthetic quark/gluon jet images, 125x125x3 (Tracks / ECAL / HCAL).

Physics-motivated stand-in, NOT real CMS data. The real Andrews et al.
125x125x3 dataset (933,206 images) has no direct free download: every
public source says access is via the project maintainer / ML4SCI.
So this generator encodes the one robust, published class difference
(quark jets are narrower with fewer particles; gluon jets are broader
with more particles) as 2-D Gaussian particle showers on an (eta, phi)
grid, with per-channel widths. Labels are known by construction, so
classifier accuracy here measures "pipeline works", NOT real physics
performance. See README.md for limits.
"""
import numpy as np

GRID = 125
EXTENT = 0.8  # eta, phi in [-0.8, 0.8]
SEED = 42


def make_jet(rng, is_gluon):
    n = int(rng.poisson(28 if is_gluon else 18)) + 6
    # Width ranges OVERLAP on purpose: real quark/gluon widths overlap
    # (gluons are broader on average, not always). Non-overlapping ranges
    # made the first version trivially separable (ROC-AUC 1.0) and the
    # classifier numbers meaningless.
    sig = rng.uniform(0.12, 0.22) if is_gluon else rng.uniform(0.08, 0.15)
    eta = rng.normal(0.0, sig, n)
    phi = rng.normal(0.0, sig, n)
    pt = rng.exponential(1.0, n) + 0.2
    # core particle near the jet axis
    eta[0], phi[0], pt[0] = rng.normal(0, 0.01), rng.normal(0, 0.01), 3.0
    coords = np.linspace(-EXTENT, EXTENT, GRID, dtype=np.float32)
    xx, yy = np.meshgrid(coords, coords)  # xx: phi axis, yy: eta axis
    img = np.zeros((3, GRID, GRID), dtype=np.float32)
    # channel: (width multiplier, amplitude)
    for c, (wm, amp) in enumerate([(0.8, 1.0), (1.0, 0.8), (1.5, 0.6)]):
        s = sig * wm
        dx = xx[None, :, :] - phi[:, None, None]
        dy = yy[None, :, :] - eta[:, None, None]
        # unit-integral Gaussian per particle, so a wider shower is more
        # spread out, NOT brighter: total energy must not leak the label.
        kern = np.exp(-(dx * dx + dy * dy) / (2 * s * s)) / (2 * np.pi * s * s)
        img[c] = (amp * pt[:, None, None] * kern).sum(axis=0)
    # match jets to the same total energy: only the SHAPE may differ
    # between quark and gluon (width / particle count), as in real jets
    # selected in a fixed pT range.
    img *= (1000.0 / img.sum())
    # sparse background noise on ~2% of pixels only: real jet images are
    # >99% empty, so the stand-in must be sparse too.
    noise_mask = rng.random(size=img.shape) < 0.02
    img += (noise_mask * rng.exponential(0.005, size=img.shape)).astype(np.float32)
    return img


def main(n_per_class=600, out="data/synth_jets.npz"):
    rng = np.random.default_rng(SEED)
    xs, ys = [], []
    for label in (0, 1):  # 0 = quark, 1 = gluon
        for _ in range(n_per_class):
            xs.append(make_jet(rng, bool(label)))
            ys.append(label)
    x = np.stack(xs).astype(np.float32)
    y = np.array(ys, dtype=np.int64)
    # shuffle with fixed seed
    idx = rng.permutation(len(y))
    np.savez_compressed(out, x=x[idx], y=y[idx])
    print(f"saved {out}: x={x.shape} y={y.shape} "
          f"quark={int((y==0).sum())} gluon={int((y==1).sum())} "
          f"nonzero_frac={float((x>0).mean()):.3f} max={float(x.max()):.2f}")


if __name__ == "__main__":
    main()
