"""Run the experiment: from-scratch CART vs sklearn on breast cancer.

Dataset: sklearn's bundled Wisconsin Breast Cancer dataset
(569 tumours, 30 numeric features from cell-nucleus images,
label 0 = malignant, 1 = benign). Bundled with scikit-learn, so
no download is needed. This is a real, standard benchmark dataset
— not synthetic data.

Models compared on the same stratified 80/20 split (seed 42):
  1. Our from-scratch CART, max_depth=3 (interpretable)
  2. Our from-scratch CART, max_depth=None (full tree)
  3. sklearn DecisionTreeClassifier, max_depth=3 (same depth, sanity check)
  4. sklearn RandomForestClassifier, 200 trees (strong baseline)

Metrics: accuracy, confusion matrix, and the top-5 features by
importance for the from-scratch tree. Results are printed and
saved to results.json (numbers in the README come from this run).
"""

import json

from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier as SkTree

from tree import DecisionTreeClassifier


def evaluate(name, y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred).tolist()
    return {
        "model": name,
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "confusion_matrix": cm,  # [[true0 pred0, true0 pred1],
                                 #  [true1 pred0, true1 pred1]]
    }


def main():
    data = load_breast_cancer()
    X, y = data.data.tolist(), data.target.tolist()
    names = list(data.feature_names)
    print(f"Dataset: {len(y)} samples, {len(names)} features, "
          f"classes 0=malignant ({y.count(0)}), 1=benign ({y.count(1)})")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"Train: {len(y_train)}, test: {len(y_test)} "
          f"(stratified, seed 42)\n")

    results = {"dataset": "sklearn Wisconsin Breast Cancer (bundled)",
               "n_train": len(y_train), "n_test": len(y_test),
               "models": []}

    # 1 & 2. From-scratch CART at two depths.
    for depth in (3, None):
        tree = DecisionTreeClassifier(max_depth=depth).fit(X_train, y_train)
        pred = tree.predict(X_test)
        label = f"from-scratch CART (max_depth={depth})"
        row = evaluate(label, y_test, pred)
        row["tree_depth"] = tree.depth_
        results["models"].append(row)
        print(f"{label}: accuracy {row['accuracy']:.4f}, "
              f"tree depth {tree.depth_}")
        if depth == 3:
            results["top_features"] = [
                {"feature": names[i],
                 "importance": round(v, 4)}
                for i, v in sorted(
                    enumerate(tree.feature_importances_),
                    key=lambda t: -t[1])[:5]
            ]
            print("\nTop 5 features (from-scratch tree):")
            for f in results["top_features"]:
                print(f"  {f['feature']}: {f['importance']}")
            print("\nLearned tree (depth 3):")
            print(tree.print_tree(feature_names=names))

    # 3. sklearn tree at the same depth — should be close to ours.
    sk = SkTree(max_depth=3, random_state=42).fit(X_train, y_train)
    row = evaluate("sklearn DecisionTree (max_depth=3)",
                   y_test, sk.predict(X_test))
    results["models"].append(row)
    print(f"\nsklearn DecisionTree (max_depth=3): "
          f"accuracy {row['accuracy']:.4f}")

    # 4. Random forest — the strong-baseline ceiling.
    rf = RandomForestClassifier(n_estimators=200, random_state=42,
                                n_jobs=-1).fit(X_train, y_train)
    row = evaluate("sklearn RandomForest (200 trees)",
                   y_test, rf.predict(X_test))
    results["models"].append(row)
    print(f"sklearn RandomForest (200 trees): accuracy {row['accuracy']:.4f}")

    print("\nConfusion matrices (rows = true, cols = predicted; "
          "0 = malignant, 1 = benign):")
    for row in results["models"]:
        print(f"  {row['model']}: {row['confusion_matrix']}")

    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved results.json")


if __name__ == "__main__":
    main()
