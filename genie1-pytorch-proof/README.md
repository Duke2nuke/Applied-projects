# GENIE1 local proof — PyTorch pipeline (LOCAL ONLY)

ML4SCI GENIE1 test prep for GSoC 2027. **Not submitted, not pushed,
no mentor contact.** Work in `~/workspace/gsoc-prep/ml4sci-genie1/work/`.
CERN account is blocked (third reset link requested 11 Nov 2026, awaited);
nothing here touches CERN.

## What this is

A small, honest, CPU-runnable PyTorch pipeline covering all three GENIE1
test tasks in miniature:

| Test task | Script | What it does |
|---|---|---|
| Task 1 — autoencoder | `train_ae.py` | Conv AE (latent 128) on 125x125x3 jet images; original vs reconstructed figure in `outputs/reconstruction.png` |
| Image baseline | `train_cnn.py` | Small CNN quark/gluon classifier on the same images |
| Task 2 — jets as graphs | `train_gnn.py` | Mean-aggregation GNN (pure PyTorch, no PyTorch Geometric) on real JetNet point clouds, k=8 NN edges |
| Specific Task 1 — contrastive | `train_contrastive.py` | NT-Xent (tau 0.2, node-dropout views) + frozen-encoder logistic probe, same split as Task 2 |

## Data — read this before quoting any number

**The real GENIE1 test dataset was NOT used.** The Andrews et al.
125x125x3 CMS dataset (933,206 images) has no direct free download:
every public source says access is via the project maintainer / ML4SCI
(e.g. the qcnn-hep README: "contact the project maintainer who can
connect you with the ML4SCI organization"). That link is still the
first blocker for the real test; it needs the CERN/ML4SCI channel,
which is currently blocked on the account reset.

Two stand-ins were used instead, both labelled everywhere:

1. **Synthetic 125x125x3 images** (`synth_jets.py`, 1,200 jets, 600/class).
   Physics-motivated: quark jets narrower (sigma 0.08–0.15) with fewer
   particles (Poisson 18); gluon jets broader (sigma 0.12–0.22) with more
   (Poisson 28). Width ranges deliberately OVERLAP (real widths overlap).
   Total energy is normalised per jet, so only shape can leak the label.
   Channels: Tracks (sharpest), ECAL, HCAL (broadest). Limits: Gaussian
   showers, not real detector simulation; no pileup, no real noise model;
   images are dense-tailed Gaussians, not >99% sparse like real jets.
   The first version had non-overlapping widths and scored ROC-AUC 1.0 —
   that was a generator bug, not a result; it was fixed and re-run.
2. **Real JetNet quark/gluon point clouds** (`jetnet_graphs.py`, 4,000 jets).
   Zenodo record 6975118 (v2, CC-BY 4.0, Kansal et al. arXiv:2106.11535),
   verified via the Zenodo API on 11 Nov 2026; direct links
   `https://zenodo.org/api/records/6975118/files/{q,g}.hdf5/content`
   (q.hdf5 84,658,832 B, 170,679 jets; g.hdf5 87,919,040 B, 177,252 jets).
   Each jet: 30 particles x [eta_rel, phi_rel, pt_rel, mask], ~1 TeV jets.
   Sanity check passed: gluon jets really do have more particles
   (29.89 vs 27.37 per jet in the sample). Limit: these are point clouds,
   not the 125x125x3 CMS images, and not the GENIE1 test data.

## Measured results (seed 42, CPU, 11 Nov 2026)

Full numbers in `results.md` and `outputs/*_metrics.json`.

- **Autoencoder** (synthetic, 800/200/200): test MSE **0.0089**
  (train 0.0091, val 0.0095) on log1p+standardised pixels. Per channel:
  Tracks 0.0138, ECAL 0.0069, HCAL 0.0062. Reconstructions visibly match
  originals in position/width per channel; the bottleneck smooths out
  fine speckle (see figure).
- **CNN classifier** (synthetic, same split): test accuracy **0.845**,
  ROC-AUC **0.933**, precision 0.963, recall 0.738, F1 0.836.
  Confusion [[90, 3], [28, 79]]. Val acc peaked at epoch 5 (0.845) then
  wobbled — mild overfitting on 800 training jets.
- **GNN classifier** (real JetNet, 2800/600/600): test accuracy **0.715**,
  ROC-AUC **0.792**, precision 0.642, recall 0.859, F1 0.735.
  Confusion [[192, 132], [39, 237]] — biased toward gluon (132 quarks
  called gluon). Real data is much harder than the synthetic images.
- **Contrastive probe** (real JetNet, same split): test accuracy **0.707**,
  ROC-AUC **0.789**, F1 0.725. Essentially tied with the GNN baseline,
  0.003 AUC below it — it does **not** beat the baseline. Likely reasons:
  only 6 contrastive epochs; node-dropout views destroy the multiplicity
  cue (dropping particles is exactly the signal); frozen probe vs the
  GNN's end-to-end head. Next step is fine-tuning end-to-end and/or the
  GLADC perturbed-weights view instead of dropout. This is reported as
  a miss, not hidden.

## Reproduce

```bash
cd work
python3 -m venv .venv
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r requirements.txt
.venv/bin/python synth_jets.py        # synthetic 125x125x3 images
.venv/bin/python jetnet_graphs.py     # needs data/q.hdf5, data/g.hdf5 (Zenodo, see above)
bash run_all.sh                       # trains AE, CNN, GNN, contrastive; ~30 min on 4 shared CPUs
```

All scripts are deterministic (seed 42). No GPU, no payment, no sign-in
to Colab/Kaggle, no GitHub push, no form submission.

## Files

- `synth_jets.py`, `jetnet_graphs.py` — data builders
- `models.py` — ConvAE, CNNClassifier, GraphEncoder/GNNClassifier, ContrastiveModel
- `train_ae.py`, `train_cnn.py`, `train_gnn.py`, `train_contrastive.py`
- `data/` — `q.hdf5`, `g.hdf5` (JetNet, Zenodo), `synth_jets.npz`, `jetnet_graphs.npz`
- `outputs/` — `*_metrics.json`, `*.pt` checkpoints, `reconstruction.png`
- `results.md` — numbers table; `requirements.txt`; `run_all.sh`

## Still missing for the real GENIE1 test

1. The real 125x125x3 dataset link (in the test doc; needs CERN/ML4SCI access).
2. GPU time for a real-scale run (10k+ jets; this VM's CPU took ~30 min for 1.2k synthetic + 4k JetNet jets).
3. CERN account / Mattermost access (third reset link awaited).
4. The contrastive model beating the GNN baseline (see miss above).
5. 2027 carryover unverified: the 2026 test/projects/mentors may change.
