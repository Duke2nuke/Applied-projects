# scikit-learn Evaluation Classifier — Proof Project

Local proof build for GSoC 2027 preparation (NumFOCUS / scikit-learn).
**Local only — not pushed to GitHub, not submitted to scikit-learn,
not affiliated with scikit-learn.** Built to show a properly evaluated
classifier on a real dataset, with reproducible numbers.

## Dataset

`sklearn.datasets.load_breast_cancer` — a real built-in dataset,
not hand-written synthetic data.

- 569 samples, 30 features, binary target: 0 = malignant, 1 = benign
- Train/test: stratified 80/20 split, `random_state=42`
  (455 train / 114 test; test: 42 malignant, 72 benign)
- 5-fold stratified cross-validation on the training set

## Models

Both as pipelines with `random_state=42`:

1. **LogisticRegression** — `StandardScaler` + `LogisticRegression(max_iter=1000)`
2. **RandomForestClassifier** — `StandardScaler` + `RandomForestClassifier(n_estimators=200)`

## Results (held-out test set, n = 114)

| Model | CV accuracy | CV F1 (macro) | Test accuracy | Test precision (macro) | Test recall (macro) | Test F1 (macro) |
|---|---|---|---|---|---|---|
| Logistic Regression | 0.9780 ± 0.0098 | 0.9764 ± 0.0106 | **0.9825** | **0.9812** | **0.9812** | **0.9812** |
| Random Forest | 0.9626 ± 0.0179 | 0.9602 ± 0.0188 | 0.9561 | 0.9551 | 0.9504 | 0.9526 |

Confusion matrices (rows = true, cols = predicted, order malignant, benign):

- Logistic Regression: `[[41, 1], [1, 71]]` — 2 errors out of 114
- Random Forest: `[[39, 3], [2, 70]]` — 5 errors out of 114

Classification report, Logistic Regression:

```
              precision    recall  f1-score   support
   malignant       0.98      0.98      0.98        42
      benign       0.99      0.99      0.99        72
    accuracy                           0.98       114
   macro avg       0.98      0.98      0.98       114
```

Classification report, Random Forest:

```
              precision    recall  f1-score   support
   malignant       0.95      0.93      0.94        42
      benign       0.96      0.97      0.97        72
    accuracy                           0.96       114
   macro avg       0.96      0.95      0.95       114
```

Honest comparison: Logistic Regression wins on every test metric
(+0.026 accuracy, +0.029 macro F1) and is more stable across CV folds.
Random Forest is worse here, notably on malignant recall (0.93 vs 0.98).
No hyperparameter tuning was done for either model; these are
out-of-the-box defaults (plus scaling for the linear model).

Full numbers, including per-class precision/recall/F1, are in `metrics.json`.

## How to run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python sklearn_eval.py        # trains, evaluates, writes metrics.json
.venv/bin/python -m pytest test_sklearn_eval.py -v   # 5 tests
```

Verified: Python 3.12.3, scikit-learn 1.9.1, 5/5 tests passing.

## Files

- `sklearn_eval.py` — data loading, models, CV + test evaluation, writes `metrics.json`
- `test_sklearn_eval.py` — 5 tests (data, stratified split, training, reproducible metrics, metrics output)
- `metrics.json` — exact recorded metrics
- `requirements.txt` — dependencies

## Limits

- Built-in dataset only; this is a pipeline/evaluation proof, not a
  real-world medical deployment. A 0.98 accuracy on 114 held-out
  samples does not mean the model is safe or useful for diagnosis.
- No tuning, no calibration, no feature-importance analysis, no
  comparison against a published baseline.
- No contribution to scikit-learn itself: no issue claimed, no PR opened,
  no maintainer contact about this project.
