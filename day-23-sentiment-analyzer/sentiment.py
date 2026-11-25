"""Sentiment Analyzer — Day 23 (Day B: AI/ML Python).

Binary sentiment classification (positive / negative) of short review
sentences, TF-IDF + Logistic Regression vs Multinomial Naive Bayes.

Data: UCI "Sentiment Labelled Sentences" (Kotzias et al., 2015) —
3,000 real labelled sentences, 1,000 each from Amazon product reviews,
IMDb movie reviews and Yelp restaurant reviews. Files live in data/
unchanged; see data/DATA_SOURCE.md for attribution.

Usage:
    python sentiment.py eval [--out metrics.json]
    python sentiment.py predict "I love this, it works great"
    python sentiment.py predict --model nb "Terrible, broke in a day"
    python -m unittest test_sentiment -v
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB

DATA_DIR = Path(__file__).resolve().parent / "data"
SOURCES = ("amazon", "imdb", "yelp")
FILES = {
    "amazon": "amazon_cells_labelled.txt",
    "imdb": "imdb_labelled.txt",
    "yelp": "yelp_labelled.txt",
}


def load_data(data_dir: Path = DATA_DIR) -> list[dict]:
    """Load all three labelled files.

    Returns a list of {"text": str, "label": int, "source": str}.
    Each file line is: <sentence>\\t<0|1>.
    """
    rows: list[dict] = []
    for source in SOURCES:
        path = data_dir / FILES[source]
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            text, _, label = line.rpartition("\t")
            text = text.strip()
            if not text:
                continue
            rows.append({"text": text, "label": int(label), "source": source})
    return rows


def make_vectorizer() -> TfidfVectorizer:
    # Word unigrams + bigrams ("not good" matters), sublinear TF so a
    # word repeated 5 times does not count 5x as much.
    return TfidfVectorizer(
        lowercase=True, ngram_range=(1, 2), min_df=2, sublinear_tf=True
    )


def make_models() -> dict[str, object]:
    return {
        "logreg": LogisticRegression(max_iter=1000, C=1.0),
        "nb": MultinomialNB(alpha=0.1),
    }


def train(rows: list[dict], model_name: str = "logreg"):
    """Fit vectorizer + model on all rows. Returns (vectorizer, model)."""
    vectorizer = make_vectorizer()
    X = vectorizer.fit_transform([r["text"] for r in rows])
    y = [r["label"] for r in rows]
    model = make_models()[model_name]
    model.fit(X, y)
    return vectorizer, model


def predict_text(vectorizer, model, text: str) -> dict:
    """Predict one sentence. Returns {"label", "probability"}."""
    if not text or not text.strip():
        raise ValueError("empty input: give a non-empty sentence")
    X = vectorizer.transform([text])
    label = int(model.predict(X)[0])
    proba = model.predict_proba(X)[0]
    return {"label": label, "probability": float(proba[label])}


def evaluate(rows: list[dict], test_size: float = 0.2, seed: int = 42) -> dict:
    """Stratified split, train both models, report metrics + per-source accuracy."""
    train_rows, test_rows = train_test_split(
        rows, test_size=test_size, random_state=seed,
        stratify=[r["label"] for r in rows],
    )
    results: dict = {
        "n_train": len(train_rows),
        "n_test": len(test_rows),
        "test_size": test_size,
        "seed": seed,
        "models": {},
    }
    for name in ("logreg", "nb"):
        vectorizer, model = train(train_rows, name)
        X_test = vectorizer.transform([r["text"] for r in test_rows])
        y_test = [r["label"] for r in test_rows]
        y_pred = model.predict(X_test)
        per_source: dict[str, float] = {}
        for source in SOURCES:
            idx = [i for i, r in enumerate(test_rows) if r["source"] == source]
            per_source[source] = round(
                accuracy_score(
                    [y_test[i] for i in idx], [int(y_pred[i]) for i in idx]
                ),
                4,
            )
        results["models"][name] = {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "macro_f1": round(float(f1_score(y_test, y_pred, average="macro")), 4),
            "confusion_matrix": [
                [int(v) for v in row] for row in confusion_matrix(y_test, y_pred)
            ],
            "per_source_accuracy": per_source,
            "classification_report": classification_report(
                y_test, y_pred, target_names=["negative", "positive"],
                digits=4, output_dict=False,
            ),
        }
    return results


def cmd_eval(args: argparse.Namespace) -> int:
    rows = load_data()
    results = evaluate(rows)
    for name, m in results["models"].items():
        print(f"{name}: accuracy={m['accuracy']} macro_f1={m['macro_f1']}")
        print(f"  confusion [[TN, FP], [FN, TP]] = {m['confusion_matrix']}")
        print(f"  per-source accuracy: {m['per_source_accuracy']}")
    out = Path(args.out)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    rows = load_data()
    vectorizer, model = train(rows, args.model)
    result = predict_text(vectorizer, model, args.text)
    word = "positive" if result["label"] == 1 else "negative"
    print(f"{word} (p={result['probability']:.3f})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sentiment analyzer for short reviews")
    sub = parser.add_subparsers(dest="command", required=True)

    p_eval = sub.add_parser("eval", help="train/evaluate both models, write metrics.json")
    p_eval.add_argument("--out", default="metrics.json")
    p_eval.set_defaults(func=cmd_eval)

    p_pred = sub.add_parser("predict", help="predict sentiment of one sentence")
    p_pred.add_argument("text")
    p_pred.add_argument("--model", choices=["logreg", "nb"], default="logreg")
    p_pred.set_defaults(func=cmd_predict)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
