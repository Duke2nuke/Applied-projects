# PyTorch Classifier — proof project

A small PyTorch image classifier: an MLP (64 → 32 → 10) trained on the
public **sklearn Digits** dataset (1,797 handwritten 8×8 digit images,
10 classes). CPU-only, fixed seed (42), 30 epochs.

## What it proves

- **PyTorch**: model definition, training loop, Adam + cross-entropy, saving/loading state dicts.
- **ML evaluation**: stratified train/test split, held-out accuracy.

## Measured result

Run `python train.py` — it prints the real held-out test accuracy and
writes `metrics.json`:

- **Test accuracy: 0.9722** (360 held-out images, measured 10 Nov 2026)
- Train size: 1,437 images

## Run it

```bash
pip install -r requirements.txt   # CPU torch
python train.py                   # trains and writes metrics.json
python test_classifier.py         # re-runs training, asserts accuracy >= 0.90
```

## Honest caveats

- Digits is a tiny, clean, well-separated dataset — 0.97 here says the
  pipeline works, not that it generalises to messy real images.
- `model.pt` is generated locally and is not committed.
- This is a proof-of-skill demo, not a production model. No claim of
  "mastery" — it shows the project was built, trained, and measured.
