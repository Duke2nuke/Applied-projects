"""TF-IDF + Logistic Regression grievance classifier for seva-triage.

Trains in seconds on the 66 hand-written synthetic grievances in data.py.
No model file is committed; the app retrains at startup.
"""

from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from data import DEPARTMENTS, load_data

SUGGESTED_NEXT_STEP = {
    "Water Supply": "Forward to the municipal water supply engineer; log the complaint and share the tanker/repair reference number.",
    "Electricity": "Forward to the electricity distribution engineer; log the complaint and share the fault reference number.",
    "Roads & Transport": "Forward to the roads / public works engineer; log the location and share the repair reference number.",
    "Health": "Forward to the district health officer / hospital superintendent; flag as urgent if a patient is affected.",
    "Education": "Forward to the district education officer / school head; log the school name and share the reference number.",
    "Revenue & Certificates": "Forward to the revenue / tehsil office; share the application number and expected timeline.",
}


def build_pipeline():
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
            ("clf", LogisticRegression(max_iter=1000, C=1.0)),
        ]
    )


def train_full():
    """Train on all 66 examples (what the API uses)."""
    texts, labels = load_data()
    model = build_pipeline()
    model.fit(texts, labels)
    return model


def evaluate():
    """Train/test split evaluation. Returns (metrics dict, report string)."""
    texts, labels = load_data()
    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.25, random_state=42, stratify=labels
    )
    model = build_pipeline()
    model.fit(x_train, y_train)
    predicted = model.predict(x_test)
    metrics = {
        "n_total": len(texts),
        "n_train": len(x_train),
        "n_test": len(x_test),
        "accuracy": round(accuracy_score(y_test, predicted), 4),
        "macro_f1": round(f1_score(y_test, predicted, average="macro"), 4),
        "department_counts": dict(sorted(Counter(labels).items())),
    }
    report = classification_report(y_test, predicted, labels=DEPARTMENTS, zero_division=0)
    return metrics, report


def predict(model, text):
    """Return (department, confidence) for one grievance text."""
    proba = model.predict_proba([text])[0]
    idx = int(proba.argmax())
    return model.classes_[idx], round(float(proba[idx]), 4)
