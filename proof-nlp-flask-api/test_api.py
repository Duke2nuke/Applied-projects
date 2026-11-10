"""Tests for the NLP Flask API, using Flask's test client (no live server)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app import METRICS, app  # noqa: E402

CLIENT = app.test_client()


def test_health():
    r = CLIENT.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_predict_spam_and_ham():
    # Paraphrases NOT in the training set, so this tests generalisation,
    # not memorisation of training examples.
    spam = CLIENT.post("/predict", json={
        "text": "You have won a free holiday, click the link to claim your prize today."})
    assert spam.status_code == 200
    assert spam.get_json()["label"] == "spam"
    ham = CLIENT.post("/predict", json={
        "text": "Can we reschedule our meeting to Thursday afternoon to review the notes?"})
    assert ham.status_code == 200
    assert ham.get_json()["label"] == "ham"


def test_predict_rejects_empty():
    r = CLIENT.post("/predict", json={"text": "   "})
    assert r.status_code == 400


def test_measured_metrics():
    assert METRICS["test_size"] == 15
    assert METRICS["accuracy"] >= 0.85, METRICS
    assert METRICS["macro_f1"] >= 0.85, METRICS


if __name__ == "__main__":
    test_health()
    test_predict_spam_and_ham()
    test_predict_rejects_empty()
    test_measured_metrics()
    print("All tests passed.")
