"""Tests for the from-scratch CART implementation (tree.py).

Unit tests need only the standard library. The last test uses
sklearn's bundled breast-cancer dataset and is skipped if sklearn
is not installed.
"""

import unittest

from tree import DecisionTreeClassifier, gini, majority_label


class TestGini(unittest.TestCase):
    def test_pure_node_is_zero(self):
        self.assertEqual(gini([0, 0, 0]), 0.0)
        self.assertEqual(gini([1, 1]), 0.0)

    def test_even_split_is_half(self):
        self.assertAlmostEqual(gini([0, 1]), 0.5)
        self.assertAlmostEqual(gini([0, 0, 1, 1]), 0.5)

    def test_empty_is_zero(self):
        self.assertEqual(gini([]), 0.0)

    def test_majority_label_tie_breaks_to_zero(self):
        self.assertEqual(majority_label([0, 1]), 0)
        self.assertEqual(majority_label([1, 1, 0]), 1)


class TestTreeOnToyData(unittest.TestCase):
    def test_perfectly_separable_single_feature(self):
        # Label is 1 exactly when x > 5.
        X = [[float(i)] for i in range(10)]
        y = [0 if i <= 5 else 1 for i in range(10)]
        tree = DecisionTreeClassifier().fit(X, y)
        self.assertEqual(tree.predict(X), y)
        self.assertEqual(tree.depth_, 1)

    def test_depth_limit_is_respected(self):
        X = [[float(i), float(i % 3)] for i in range(40)]
        y = [i % 2 for i in range(40)]
        tree = DecisionTreeClassifier(max_depth=2).fit(X, y)
        self.assertLessEqual(tree.depth_, 2)

    def test_constant_feature_never_splits(self):
        X = [[1.0, float(i)] for i in range(10)]
        y = [0 if i < 5 else 1 for i in range(10)]
        tree = DecisionTreeClassifier().fit(X, y)
        self.assertEqual(tree.feature_importances_[0], 0.0)
        self.assertEqual(tree.predict(X), y)

    def test_importances_sum_to_one(self):
        X = [[float(i), float(10 - i), float(i % 2)] for i in range(30)]
        y = [0 if i < 15 else 1 for i in range(30)]
        tree = DecisionTreeClassifier(max_depth=3).fit(X, y)
        self.assertAlmostEqual(sum(tree.feature_importances_), 1.0)

    def test_print_tree_mentions_split_and_leaf(self):
        X = [[float(i)] for i in range(10)]
        y = [0 if i <= 5 else 1 for i in range(10)]
        tree = DecisionTreeClassifier().fit(X, y)
        text = tree.print_tree(feature_names=["x"])
        self.assertIn("if x <=", text)
        self.assertIn("predict", text)

    def test_predicts_unseen_values(self):
        X = [[float(i)] for i in range(10)]
        y = [0 if i <= 5 else 1 for i in range(10)]
        tree = DecisionTreeClassifier().fit(X, y)
        self.assertEqual(tree.predict([[2.0], [9.0]]), [0, 1])


class TestTreeOnRealData(unittest.TestCase):
    def test_breast_cancer_accuracy(self):
        try:
            from sklearn.datasets import load_breast_cancer
            from sklearn.metrics import accuracy_score
            from sklearn.model_selection import train_test_split
        except ImportError:
            self.skipTest("scikit-learn not installed")
        data = load_breast_cancer()
        X_train, X_test, y_train, y_test = train_test_split(
            data.data.tolist(), data.target.tolist(),
            test_size=0.2, random_state=42, stratify=data.target)
        tree = DecisionTreeClassifier(max_depth=3).fit(X_train, y_train)
        acc = accuracy_score(y_test, tree.predict(X_test))
        # A depth-3 tree should clear 90% on this benchmark; the
        # run.py result is ~0.93. Guard against regressions, not
        # the exact number.
        self.assertGreaterEqual(acc, 0.90)
        print(f"\nfrom-scratch CART (depth 3) test accuracy: {acc:.4f}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
