"""Synthetic housing data for Day 08.

Clearly synthetic demo data, NOT real house prices. The generator uses
known true weights plus Gaussian noise, so the regression can be judged
on whether it recovers roughly the right weights -- not just on R^2.

Features (in order): size_sqft, bedrooms, age_years, distance_km.
True price model:
    price = 50000 + 150*size + 12000*bedrooms
            - 800*age - 2000*distance + noise, noise ~ N(0, 15000)
"""

import random

FEATURES = ["size_sqft", "bedrooms", "age_years", "distance_km"]
TRUE_INTERCEPT = 50000.0
TRUE_WEIGHTS = [150.0, 12000.0, -800.0, -2000.0]


def generate(n=200, seed=42):
    """Return (X, y): X is a list of feature rows, y a list of prices."""
    rng = random.Random(seed)
    X, y = [], []
    for _ in range(n):
        size = rng.uniform(500, 3000)
        bedrooms = float(rng.randint(1, 5))
        age = rng.uniform(0, 40)
        distance = rng.uniform(1, 30)
        row = [size, bedrooms, age, distance]
        price = TRUE_INTERCEPT + sum(w * v for w, v in zip(TRUE_WEIGHTS, row))
        price += rng.gauss(0, 15000)
        X.append(row)
        y.append(price)
    return X, y


def train_test_split(X, y, test_frac=0.2, seed=7):
    """Deterministic shuffle split; returns X_train, X_test, y_train, y_test."""
    rng = random.Random(seed)
    idx = list(range(len(X)))
    rng.shuffle(idx)
    n_test = int(len(X) * test_frac)
    test_idx = set(idx[:n_test])
    X_train = [X[i] for i in range(len(X)) if i not in test_idx]
    y_train = [y[i] for i in range(len(X)) if i not in test_idx]
    X_test = [X[i] for i in range(len(X)) if i in test_idx]
    y_test = [y[i] for i in range(len(X)) if i in test_idx]
    return X_train, X_test, y_train, y_test
