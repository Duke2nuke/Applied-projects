"""Softmax logistic regression on Fisher's Iris dataset, pure stdlib.

Trains at startup from data/iris.csv (150 rows, shipped in the repo).
Deterministic: fixed stratified split (first 40 rows of each species go to
train, last 10 to test), zero-initialised weights, fixed learning rate and
epoch count. No third-party packages, no network, no downloads.
"""

import csv
import math
import os

SPECIES = ["setosa", "versicolor", "virginica"]
FEATURES = ["sepal_length", "sepal_width", "petal_length", "petal_width"]
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "iris.csv")


def load_data(path=DATA_PATH):
    """Return [(features, species), ...] from the Iris CSV."""
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(([float(r[k]) for k in FEATURES], r["species"]))
    return rows


def stratified_split(rows):
    """First 40 of each species -> train (120), last 10 -> test (30)."""
    train, test = [], []
    by_species = {s: [] for s in SPECIES}
    for x, y in rows:
        by_species[y].append((x, y))
    for s in SPECIES:
        train.extend(by_species[s][:40])
        test.extend(by_species[s][40:])
    return train, test


def _softmax(z):
    m = max(z)
    exps = [math.exp(v - m) for v in z]
    total = sum(exps)
    return [e / total for e in exps]


class IrisClassifier:
    """Multinomial logistic regression, full-batch gradient descent."""

    def __init__(self, epochs=600, lr=0.1):
        self.epochs = epochs
        self.lr = lr
        self.means = [0.0] * 4
        self.stds = [1.0] * 4
        self.weights = [[0.0] * 4 for _ in SPECIES]  # 3 classes x 4 features
        self.bias = [0.0] * 3
        self.train_size = 0
        self.test_size = 0

    def _standardise(self, x):
        return [(v - m) / s for v, m, s in zip(x, self.means, self.stds)]

    def fit(self, train):
        n = len(train)
        self.train_size = n
        for j in range(4):
            col = [x[j] for x, _ in train]
            self.means[j] = sum(col) / n
            var = sum((v - self.means[j]) ** 2 for v in col) / n
            self.stds[j] = math.sqrt(var) or 1.0
        xs = [self._standardise(x) for x, _ in train]
        ys = [SPECIES.index(y) for _, y in train]
        for _ in range(self.epochs):
            gw = [[0.0] * 4 for _ in SPECIES]
            gb = [0.0] * 3
            for xi, yi in zip(xs, ys):
                scores = [sum(w * v for w, v in zip(self.weights[c], xi)) + self.bias[c]
                          for c in range(3)]
                probs = _softmax(scores)
                for c in range(3):
                    err = probs[c] - (1.0 if c == yi else 0.0)
                    gb[c] += err
                    for j in range(4):
                        gw[c][j] += err * xi[j]
            for c in range(3):
                self.bias[c] -= self.lr * gb[c] / n
                for j in range(4):
                    self.weights[c][j] -= self.lr * gw[c][j] / n
        return self

    def predict_proba(self, x):
        validate_features(x)
        xs = self._standardise([float(v) for v in x])
        scores = [sum(w * v for w, v in zip(self.weights[c], xs)) + self.bias[c]
                  for c in range(3)]
        return _softmax(scores)

    def predict(self, x):
        probs = self.predict_proba(x)
        return SPECIES[max(range(3), key=lambda c: probs[c])]

    def accuracy(self, data):
        if not data:
            return 0.0
        correct = sum(1 for x, y in data if self.predict(x) == y)
        return correct / len(data)


def validate_features(x):
    """Raise ValueError unless x is 4 finite numbers."""
    if not isinstance(x, (list, tuple)) or len(x) != 4:
        raise ValueError("expected exactly 4 measurements: "
                         "sepal_length, sepal_width, petal_length, petal_width")
    for v in x:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("all 4 measurements must be numbers")
        if not math.isfinite(v):
            raise ValueError("measurements must be finite numbers")


def train_default():
    """Load data, train, and return (classifier, train, test)."""
    rows = load_data()
    train, test = stratified_split(rows)
    clf = IrisClassifier().fit(train)
    clf.test_size = len(test)
    return clf, train, test
