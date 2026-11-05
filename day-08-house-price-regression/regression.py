"""Linear regression from scratch, standard library only.

Two solvers are implemented on the same standardised features so they
can be checked against each other:

1. Gradient descent (iterative, the one to explain in an interview).
2. Closed form via the normal equations, solved with Gaussian
   elimination (the exact answer gradient descent should approach).

Standardisation (zero mean, unit variance, fitted on TRAIN only) is
essential here: size is in the thousands while bedrooms is 1-5, so
without it one gradient step size cannot suit all features.

Coefficients are converted back to original units for reporting, so
e.g. "about $150 per extra sq ft" reads directly off the model.
"""

import math


def _mean(xs):
    return sum(xs) / len(xs)


def _std(xs, mean):
    return math.sqrt(sum((x - mean) ** 2 for x in xs) / len(xs)) or 1.0


class StandardScaler:
    """Fit on train, apply to train and test (never fit on test)."""

    def fit(self, X):
        self.means_ = [_mean([row[j] for row in X]) for j in range(len(X[0]))]
        self.stds_ = [
            _std([row[j] for row in X], self.means_[j]) for j in range(len(X[0]))
        ]
        return self

    def transform(self, X):
        return [
            [(v - self.means_[j]) / self.stds_[j] for j, v in enumerate(row)]
            for row in X
        ]

    def fit_transform(self, X):
        return self.fit(X).transform(X)


def _add_bias(X):
    return [[1.0] + row for row in X]


def _predict_row(weights, row):
    return sum(w * v for w, v in zip(weights, row))


def gradient_descent(X, y, lr=0.05, epochs=2000):
    """Batch gradient descent on mean squared error. X must be standardised."""
    Xb = _add_bias(X)
    weights = [0.0] * len(Xb[0])
    n = len(Xb)
    for _ in range(epochs):
        grads = [0.0] * len(weights)
        for row, target in zip(Xb, y):
            err = _predict_row(weights, row) - target
            for j in range(len(weights)):
                grads[j] += (2.0 / n) * err * row[j]
        weights = [w - lr * g for w, g in zip(weights, grads)]
    return weights


def _solve_linear(A, b):
    """Gaussian elimination with partial pivoting. Returns x for Ax = b."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[pivot] = M[pivot], M[col]
        piv = M[col][col]
        if abs(piv) < 1e-12:
            raise ValueError("singular matrix in normal equations")
        for r in range(n):
            if r != col:
                factor = M[r][col] / piv
                for c in range(col, n + 1):
                    M[r][c] -= factor * M[col][c]
    return [M[i][n] / M[i][i] for i in range(n)]


def closed_form(X, y):
    """Exact least-squares weights via the normal equations. X standardised."""
    Xb = _add_bias(X)
    d = len(Xb[0])
    XtX = [[sum(row[i] * row[j] for row in Xb) for j in range(d)] for i in range(d)]
    Xty = [sum(row[i] * target for row, target in zip(Xb, y)) for i in range(d)]
    return _solve_linear(XtX, Xty)


def predict(weights, X):
    return [_predict_row(weights, row) for row in _add_bias(X)]


def to_original_units(weights_std, scaler):
    """Convert standardised weights to original units.

    Returns (intercept, [per-feature weights]) in the original feature
    units, so coefficients are directly interpretable.
    """
    w0 = weights_std[0]
    weights = []
    intercept = w0
    for j, (w, mean, std) in enumerate(
        zip(weights_std[1:], scaler.means_, scaler.stds_)
    ):
        weights.append(w / std)
        intercept -= w * mean / std
    return intercept, weights


def mae(y_true, y_pred):
    return sum(abs(a - b) for a, b in zip(y_true, y_pred)) / len(y_true)


def rmse(y_true, y_pred):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(y_true, y_pred)) / len(y_true))


def r2(y_true, y_pred):
    mean = _mean(y_true)
    ss_tot = sum((a - mean) ** 2 for a in y_true)
    ss_res = sum((a - b) ** 2 for a, b in zip(y_true, y_pred))
    return 1.0 - ss_res / ss_tot if ss_tot else 0.0
