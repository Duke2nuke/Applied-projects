"""Predict an Iris species from the command line.

Usage:
    python predict.py 5.1 3.5 1.4 0.2
    python predict.py 5.1 3.5 1.4 0.2 --json

Requires model.pt — run `python train.py` first if it does not exist.
Arguments are sepal length, sepal width, petal length, petal width (cm).
"""

import argparse
import json
import sys
from pathlib import Path

import torch

from model import CLASSES, IrisMLP, predict_species

HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE / "model.pt"


def load_checkpoint(path=MODEL_PATH):
    if not Path(path).exists():
        print(f"error: {path} not found — run `python train.py` first.", file=sys.stderr)
        sys.exit(1)
    ckpt = torch.load(path, map_location="cpu", weights_only=True)
    model = IrisMLP(hidden=ckpt["hidden"])
    model.load_state_dict(ckpt["state_dict"])
    return model, ckpt["mean"], ckpt["std"]


def main():
    parser = argparse.ArgumentParser(description="Predict an Iris species.")
    parser.add_argument("measurements", type=float, nargs=4,
                        metavar="MEASUREMENT",
                        help="sepal length, sepal width, petal length, petal width (cm)")
    parser.add_argument("--json", action="store_true", help="print JSON output")
    args = parser.parse_args()

    model, mean, std = load_checkpoint()
    species, probs = predict_species(model, args.measurements, mean, std)
    if args.json:
        print(json.dumps({"species": species, "probabilities": probs}))
    else:
        print(f"species: {species}")
        for name in CLASSES:
            print(f"  {name:<11} {probs[name]:.4f}")


if __name__ == "__main__":
    main()
