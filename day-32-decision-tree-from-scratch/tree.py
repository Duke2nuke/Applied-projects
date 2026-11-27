"""Decision tree classifier (CART) implemented from scratch.

Pure Python standard library only — no scikit-learn, no NumPy.
The tree itself is written out here so every step can be explained
in an interview: Gini impurity, best-split search over feature
thresholds, recursive splitting, and feature importances derived
from impurity decrease.

Public API:
    DecisionTreeClassifier(max_depth=None, min_samples_split=2)
        .fit(X, y)   X: list of rows (lists of floats), y: list of 0/1 labels
        .predict(X)  -> list of 0/1 predictions
        .feature_importances_  -> list of floats, sums to 1.0
        .print_tree(feature_names=None, max_lines=None) -> str

sklearn is used only in run.py (to load the bundled dataset and to
compare against its own DecisionTreeClassifier) — never inside this
module.
"""


def gini(labels):
    """Gini impurity of a list of class labels (0/1)."""
    n = len(labels)
    if n == 0:
        return 0.0
    p1 = sum(labels) / n
    return 1.0 - p1 * p1 - (1.0 - p1) * (1.0 - p1)


def majority_label(labels):
    """Most common label; ties break towards 0 (benign)."""
    return 1 if sum(labels) * 2 > len(labels) else 0


class _Node:
    __slots__ = ("feature", "threshold", "left", "right", "label",
                 "n_samples", "impurity")

    def __init__(self, label, n_samples, impurity):
        self.feature = None      # split feature index (None = leaf)
        self.threshold = None    # split threshold (None = leaf)
        self.left = None
        self.right = None
        self.label = label       # majority label at this node
        self.n_samples = n_samples
        self.impurity = impurity


class DecisionTreeClassifier:
    """Binary CART decision tree, Gini impurity, best-split search."""

    def __init__(self, max_depth=None, min_samples_split=2):
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.root_ = None
        self.n_features_ = 0
        self.feature_importances_ = []
        self.depth_ = 0

    # -- fitting ------------------------------------------------------
    def fit(self, X, y):
        X = [list(map(float, row)) for row in X]
        y = [int(v) for v in y]
        self.n_features_ = len(X[0]) if X else 0
        self._importances = [0.0] * self.n_features_
        self.root_ = self._build(X, y, depth=0)
        total = sum(self._importances)
        self.feature_importances_ = (
            [v / total for v in self._importances] if total > 0
            else [0.0] * self.n_features_
        )
        return self

    def _best_split(self, X, y):
        """Return (feature, threshold, gain) of the best split, or None."""
        n = len(y)
        parent_impurity = gini(y)
        best = None  # (gain, feature, threshold)
        for feature in range(self.n_features_):
            values = sorted({row[feature] for row in X})
            if len(values) < 2:
                continue
            # Candidate thresholds: midpoints between distinct values.
            for a, b in zip(values, values[1:]):
                threshold = (a + b) / 2.0
                left_y = [yy for row, yy in zip(X, y)
                          if row[feature] <= threshold]
                right_y = [yy for row, yy in zip(X, y)
                           if row[feature] > threshold]
                if not left_y or not right_y:
                    continue
                weighted = (len(left_y) * gini(left_y)
                            + len(right_y) * gini(right_y)) / n
                gain = parent_impurity - weighted
                if best is None or gain > best[0]:
                    best = (gain, feature, threshold)
        if best is None or best[0] <= 0:
            return None
        return best

    def _build(self, X, y, depth):
        node = _Node(majority_label(y), len(y), gini(y))
        self.depth_ = max(self.depth_, depth)
        if len(y) < self.min_samples_split:
            return node
        if self.max_depth is not None and depth >= self.max_depth:
            return node
        if node.impurity == 0.0:
            return node
        split = self._best_split(X, y)
        if split is None:
            return node
        gain, feature, threshold = split
        left_idx = [i for i, row in enumerate(X)
                    if row[feature] <= threshold]
        right_idx = [i for i, row in enumerate(X)
                     if row[feature] > threshold]
        # Impurity decrease credited to this feature (importance).
        self._importances[feature] += gain * len(y)
        node.feature, node.threshold = feature, threshold
        node.left = self._build([X[i] for i in left_idx],
                                [y[i] for i in left_idx], depth + 1)
        node.right = self._build([X[i] for i in right_idx],
                                 [y[i] for i in right_idx], depth + 1)
        return node

    # -- prediction ---------------------------------------------------
    def predict(self, X):
        return [self._predict_one(list(map(float, row))) for row in X]

    def _predict_one(self, row):
        node = self.root_
        while node.feature is not None:
            if row[node.feature] <= node.threshold:
                node = node.left
            else:
                node = node.right
        return node.label

    # -- inspection ---------------------------------------------------
    def print_tree(self, feature_names=None, max_lines=None):
        """Readable text rendering of the learned tree."""
        names = feature_names or [f"feature_{i}"
                                  for i in range(self.n_features_)]
        lines = []

        def walk(node, prefix):
            if len(lines) == max_lines:
                return
            if node.feature is None:
                lines.append(
                    f"{prefix}predict {node.label} "
                    f"({node.n_samples} samples, "
                    f"gini={node.impurity:.3f})")
                return
            name = names[node.feature]
            lines.append(
                f"{prefix}if {name} <= {node.threshold:.4f}:")
            walk(node.left, prefix + "    ")
            lines.append(f"{prefix}else:  # {name} > {node.threshold:.4f}")
            walk(node.right, prefix + "    ")

        walk(self.root_, "")
        if max_lines is not None and len(lines) == max_lines:
            lines.append("... (truncated)")
        return "\n".join(lines)
