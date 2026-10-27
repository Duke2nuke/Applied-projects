"""Score one prompt: python detector.py "your prompt here"

Trains on the full synthetic dataset each run (fast, seconds),
so no model file needs to be committed.
"""

import sys

from data import load
from train import build_model


def main():
    if len(sys.argv) < 2:
        print('Usage: python detector.py "your prompt here"')
        raise SystemExit(1)
    prompt = " ".join(sys.argv[1:])
    texts, labels = load()
    model = build_model()
    model.fit(texts, labels)
    pred = model.predict([prompt])[0]
    proba = model.predict_proba([prompt])[0]
    label = "INJECTION" if pred == 1 else "benign"
    print(f"{label}  (injection probability: {proba[1]:.2f})")


if __name__ == "__main__":
    main()
