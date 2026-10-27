"""Train TF-IDF + Logistic Regression and report held-out metrics."""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from data import load


def build_model():
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )


def main():
    texts, labels = load()
    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.25, random_state=42, stratify=labels
    )
    model = build_model()
    model.fit(x_train, y_train)
    preds = model.predict(x_test)
    print(f"Test accuracy: {accuracy_score(y_test, preds):.2f}")
    print(classification_report(y_test, preds, target_names=["benign", "injection"]))


if __name__ == "__main__":
    main()
