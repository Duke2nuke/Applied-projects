"""Train a TF-IDF + Logistic Regression spam classifier on the hand-written set."""

import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from data import DATA

HERE = Path(__file__).parent


def build_model():
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(lowercase=True, stop_words="english")),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )


def train_and_eval():
    texts, labels = zip(*DATA)
    X_train, X_test, y_train, y_test = train_test_split(
        list(texts), list(labels), test_size=0.25, random_state=42, stratify=labels
    )
    model = build_model()
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    report = classification_report(
        y_test, pred, target_names=["ham", "spam"], output_dict=True, zero_division=0
    )
    metrics = {
        "dataset": "60 hand-written messages (30 ham, 30 spam), synthetic",
        "train_size": len(X_train),
        "test_size": len(X_test),
        "accuracy": round(report["accuracy"], 4),
        "ham_precision": round(report["ham"]["precision"], 4),
        "ham_recall": round(report["ham"]["recall"], 4),
        "spam_precision": round(report["spam"]["precision"], 4),
        "spam_recall": round(report["spam"]["recall"], 4),
        "spam_f1": round(report["spam"]["f1-score"], 4),
        "macro_f1": round(report["macro avg"]["f1-score"], 4),
    }
    (HERE / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"Accuracy: {metrics['accuracy']}, macro F1: {metrics['macro_f1']}")
    print(f"Spam precision: {metrics['spam_precision']}, "
          f"recall: {metrics['spam_recall']}, F1: {metrics['spam_f1']}")
    return model, metrics


if __name__ == "__main__":
    train_and_eval()
