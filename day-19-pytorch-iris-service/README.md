# Day 19 — PyTorch Iris Classifier, Served by FastAPI, with CI (Day A: trending-skill)

A small PyTorch MLP that classifies Iris flowers, served behind a
FastAPI endpoint, with a GitHub Actions CI workflow that trains the
model and runs the tests on every push. The point of this project is
the whole loop — train, evaluate, serve, and keep it green in CI —
because that is what the job data now asks for.

## The trend behind it (named, with sources)

- **PyTorch is the sharpest framework gap.** Skillenai's AI Engineer
  index (13 Nov 2026, 4,219 postings, 90 days): PyTorch in 14.9% of
  AI Engineer ads; RemoteAI's 2 Nov 2026 count of 1,903 remote AI
  roles puts PyTorch at 21% of AI/ML-titled ads. Earlier daily
  projects used scikit-learn and TensorFlow; this is the first daily
  project trained in PyTorch.
- **CI/CD is now a top-4 JD skill.** Same Skillenai index: CI/CD in
  23.8% of AI Engineer postings (1,004 of 4,219), ahead of LangChain,
  AWS and PyTorch. RemoteAI's gap table makes the point sharper:
  CI/CD appears in 15% of remote AI ads but on only 6% of talent
  profiles. This repo had no CI at all before this project — the
  workflow in `.github/workflows/day-19-ci.yml` is its first.
- **Deployment is the other half of the gap.** The same datasets put
  FastAPI / model serving next to training in the production phase,
  so the model is served over HTTP, not just evaluated in a script.

## What it does

- `train.py` trains a 4 -> 16 -> 16 -> 3 MLP (Adam, lr 0.01, 200
  epochs, seed 42) on the classic Fisher Iris dataset (150 rows,
  bundled as `iris.csv`, source: UCI Machine Learning Repository).
  Split is stratified and seeded: 102 train / 24 validation /
  24 test. It writes `model.pt` and `metrics.json`.
- `predict.py` classifies one flower from the command line.
- `serve.py` is a FastAPI app: `GET /health`, `POST /predict`
  (validated JSON, 422 on bad input, 503 if untrained),
  `GET /metrics` (the eval report).
- `.github/workflows/day-19-ci.yml` installs CPU-only PyTorch,
  trains, and runs the tests on every push/PR touching this folder.

## Results (actually run, 14 Nov 2026)

- Train accuracy 1.0000, validation accuracy 1.0000, **test accuracy
  0.9167 (22 of 24)**. Per-class test accuracy: setosa 1.0,
  versicolor 1.0, virginica 0.75 (2 of 8 virginica test rows
  classified as versicolor — the classic versicolor/virginica
  overlap). Final train loss 0.0095.
- 10/10 tests pass locally (`pytest test_iris_service.py -v`), covering
  data loading, the stratified split, model shape, training accuracy,
  all three API endpoints, input validation, and the CLI.

## How to run it

```bash
pip install -r requirements.txt   # CPU-only torch (~190 MB, no GPU needed)
python train.py                   # trains, writes model.pt + metrics.json
python predict.py 5.1 3.5 1.4 0.2
uvicorn serve:app --reload        # then POST to http://127.0.0.1:8000/predict
```

Example API call:

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2}'
# {"species": "setosa", "probabilities": {"setosa": 1.0, "versicolor": 0.0, "virginica": 0.0}}
```

`model.pt` is a binary file and is intentionally not committed — CI
and anyone cloning retrains it with `python train.py` (about 20
seconds on CPU).

## 2-minute explainer

**Problem.** Hiring data says the missing piece is not "can you train
a model" but "can you train one, serve it, and keep it tested in CI".
Most tutorials stop at the notebook. **Approach.** A small PyTorch
MLP on the Iris dataset, because the dataset is real, tiny, and
trains on CPU in seconds — the interesting part is the pipeline
around it: a seeded stratified split, standardisation from the train
set only, an eval report with per-class accuracy, a FastAPI service
with input validation, and a GitHub Actions workflow that retrains
and tests on every push. **Results.** Test accuracy 0.9167 on 24
held-out rows, with the two errors both in the known
versicolor/virginica overlap; 10/10 tests pass. **Limits.** Iris is a
toy dataset — 150 rows, 4 features, 3 well-separated classes — so the
accuracy proves the pipeline works, not that this model generalises
to any real problem. The test set is only 24 rows, so the 0.9167 has
wide error bars. No model registry, no drift monitoring, no
versioned data — the next steps for a production version.
