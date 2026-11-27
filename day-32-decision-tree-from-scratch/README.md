# Day 32 — Decision Tree from Scratch (CART) (Day B: AI/ML Python)

A decision tree classifier (CART) **implemented from scratch in pure
Python** — Gini impurity, best-split search over feature thresholds,
recursive splitting, and feature importances from impurity decrease,
all written out in `tree.py` with no NumPy and no scikit-learn
inside the model itself. It is trained and evaluated on a real
benchmark dataset, then checked against sklearn's own tree and a
random forest on the same split.

## The problem

Decision trees are the most explainable classifier in ML: unlike a
neural net or a forest, you can read the learned model as a short
list of if/else rules and show exactly why a sample got its label.
That is why they still show up in interviews, in regulated domains,
and as the base learner inside random forests and gradient boosting.
But most people have only ever *called* `DecisionTreeClassifier` —
this project is the one where you can say how it works inside.

## The data

The Wisconsin Breast Cancer dataset, bundled with scikit-learn
(`load_breast_cancer`): 569 tumours, 30 numeric features measured
from cell-nucleus images (radius, texture, concavity, …), labelled
0 = malignant (212) and 1 = benign (357). A real, standard
benchmark dataset — not synthetic data — and bundled, so no
download is needed.

**This is a benchmark exercise, not a medical tool.** A 93.9%
classifier on 114 test samples must never be presented as a
diagnostic system.

## Approach

1. Stratified 80/20 train/test split, seed 42 (455 train, 114 test).
2. From-scratch CART (`tree.py`): at each node, try every feature
   and every midpoint threshold, pick the split with the largest
   Gini gain, recurse until pure, `max_depth` reached, or fewer
   than `min_samples_split` samples remain.
3. Same split, three comparisons: sklearn's `DecisionTreeClassifier`
   at the same depth (sanity check), the from-scratch tree with no
   depth limit (overfitting check), and a 200-tree random forest
   (strong-baseline ceiling).

## Results (actually run, 27 Nov 2026 — see `results.json`)

| Model | Test accuracy | Confusion matrix* |
|---|---|---|
| From-scratch CART, depth 3 | **0.9386** | [[38, 4], [3, 69]] |
| sklearn DecisionTree, depth 3 | **0.9386** | [[38, 4], [3, 69]] |
| From-scratch CART, no depth limit | 0.9123 | [[39, 3], [7, 65]] |
| sklearn RandomForest, 200 trees | 0.9561 | [[39, 3], [2, 70]] |

\* Rows = true label, columns = predicted; 0 = malignant, 1 = benign.

Two things worth saying in an interview:

- **The from-scratch tree exactly matches sklearn's tree** at the
  same depth — same accuracy, same confusion matrix. The
  implementation is verified, not just plausible.
- **The unlimited-depth tree is worse than the depth-3 tree**
  (0.9123 vs 0.9386): it grows to depth 7 memorising training
  noise. That is overfitting you can point at, and the reason the
  depth limit exists.

Top features by importance (from-scratch tree): worst radius 0.76,
worst concave points 0.13, texture error 0.05, worst texture 0.03,
worst concavity 0.02. The learned depth-3 tree is short enough to
read in full — e.g. `worst radius <= 16.8` and `worst concave
points <= 0.136` lands in a leaf that is 270/271 benign.

## How to run

```bash
pip install -r requirements.txt   # scikit-learn, for the dataset + baselines
python3 run.py                    # train, compare, print the tree, save results.json
python3 test_tree.py              # 11 automated checks (10 stdlib-only + 1 real-data)
```

`tree.py` itself needs only the standard library; sklearn is used
only in `run.py` to load the bundled dataset and to run the
comparison models.

## 2-minute explainer

**Problem:** classify a tumour as malignant or benign from 30
measurements of its cell nuclei — and do it with a model a human
can read, not a black box.

**Approach:** I implemented CART from scratch: Gini impurity to
measure how mixed a node is, an exhaustive search over every
feature and threshold for the split that reduces impurity most,
recursion until the node is pure or the depth limit hits, and
feature importances from the total impurity decrease each feature
caused. Then I trained it on the Wisconsin Breast Cancer data and
compared it on the same split against sklearn's tree and a random
forest.

**Results:** at depth 3 my tree scores 93.86% on 114 held-out
samples — exactly matching sklearn's depth-3 tree, same confusion
matrix, so the implementation is verified. The forest reaches
95.61%. The unlimited-depth tree drops to 91.23%, which is the
overfitting lesson: deeper is not better.

**Limits:** this is a benchmark on 569 samples, not a medical
device — 4 malignant tumours in the test set are still missed,
and a real diagnostic system needs far more data, calibration,
and clinical validation. The tree also only handles binary
classification and numeric features, and the exhaustive split
search is O(features × values) per node, so it is slower than
sklearn's optimised version on large data.
