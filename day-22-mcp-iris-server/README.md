# Day 22 — MCP Iris Classifier Server (Day A: trending-skill build)

A Model Context Protocol (MCP) server, written with only the Python
standard library, that exposes a **trained Iris classifier as tools**
an AI agent can call: `predict_iris`, `predict_batch`, and
`model_info`, over newline-delimited JSON-RPC 2.0 on stdio. A
`eval_client.py` harness drives the server and grades it on a 10-case
golden set with pass/fail and per-call latency.

## The trend this builds with

**MCP depth + evals.** Two sources from the morning of 17 Nov 2026:

- The 16 Nov daily trending summary flagged MCP depth as the sharpest
  emerging gap (Stacklok survey, Oct 2026, n=520: MCP + internal-system
  integrations and multi-step agent workflows are the hardest pieces to
  migrate; roadmap.sh consolidation, 15 Nov: build one MCP server AND
  one client). Its suggested next step was exactly this: ship a tiny
  MCP server exposing the Day 19 Iris classifier as tools, plus a
  10-case eval set with pass/fail and latency log.
- Fresh search, 17 Nov: an analysis of 2,584 open agentic-AI roles
  (getreadyforagents.com, as of 16 Nov 2026) names MCP in 27% of them —
  the most-named framework/protocol — ahead of LangGraph (13%) and
  evals (9%). A 390-posting analysis (Medium, 4 Nov 2026) puts evals
  in 56% of AI-engineer postings.

This is not a repeat of Day 04 (a notes CRUD server with no model
behind it) or Day 19 (a PyTorch + FastAPI service): the new thing here
is the MCP layer around a trained model, plus the eval harness that
grades the server through the same protocol a real agent would use.

## What it does

- Trains a softmax logistic-regression classifier in pure Python at
  startup from `data/iris.csv` — Fisher's Iris dataset, 150 rows,
  shipped in the repo. Deterministic split: first 40 rows of each
  species train (120), last 10 test (30). Standardised features,
  600 epochs of full-batch gradient descent, learning rate 0.1.
- Serves the model over the MCP stdio protocol (`initialize`,
  `tools/list`, `tools/call`), so any MCP client can call it without
  knowing anything about the model code.
- `eval_client.py` sends 10 golden cases from the held-out test set
  (labels taken from the CSV, not from the server) and reports
  pass/fail and latency per call.

## How to run

```bash
python3 server.py
```

Then send one JSON object per line on stdin, for example:

```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/call",
 "params": {"name": "model_info", "arguments": {}}}
{"jsonrpc": "2.0", "id": 3, "method": "tools/call",
 "params": {"name": "predict_iris",
            "arguments": {"measurements": [5.1, 3.5, 1.4, 0.2]}}}
```

Run the eval harness (drives the server as a subprocess):

```bash
python3 eval_client.py
```

Run the automated tests (handshake, tool list, one known flower per
species, batch, model card, bad input and unknown tool):

```bash
python3 test_server.py
```

No third-party packages, no network, no API keys. Python 3.8+.

## Example input / output (actually run, 17 Nov 2026)

`model_info` reply:

```json
{"model": "softmax logistic regression (pure Python, stdlib only)",
 "classes": ["setosa", "versicolor", "virginica"],
 "features": ["sepal_length", "sepal_width", "petal_length", "petal_width"],
 "dataset": "Fisher's Iris, data/iris.csv (150 rows)",
 "train_size": 120, "test_size": 30,
 "train_accuracy": 0.9583, "test_accuracy": 1.0,
 "epochs": 600, "learning_rate": 0.1}
```

`predict_iris` for `[5.1, 3.5, 1.4, 0.2]`:

```json
{"species": "setosa",
 "probabilities": {"setosa": 0.9886, "versicolor": 0.0114, "virginica": 0.0}}
```

Eval harness (`python3 eval_client.py`):

```text
Model: softmax logistic regression | train 120 (acc 0.958) | test 30 (acc 1.000)
10/10 passed | mean latency 0.07 ms | max latency 0.16 ms
```

Tests: 9/9 pass (`python3 test_server.py`, 0.423s).

## 2-minute explainer

**Problem.** Agents need to call real tools, and the skill employers
now test is MCP: can you expose something useful as a tool an agent
can discover and call, and can you prove it works? A classifier
sitting in a notebook is not a tool; a FastAPI endpoint is not an
MCP server.

**Approach.** I took the classic Iris dataset (150 labelled flowers,
4 measurements each) and trained a softmax logistic-regression
classifier from scratch in pure Python — standardised features,
gradient descent, no sklearn, no PyTorch — so the whole thing runs
anywhere with just Python. Then I wrapped it in an MCP server over
stdio JSON-RPC, the same protocol shape as Day 04, exposing three
tools: single prediction, batch prediction, and a model card. A
separate eval client talks to the server exactly like a real MCP
client would, sends 10 held-out flowers, and grades pass/fail with
latency per call.

**Results.** Train accuracy 0.958 (115/120), held-out test accuracy
1.000 (30/30), eval golden set 10/10 passed with mean latency
0.07 ms per call. 9/9 automated tests pass, including bad-input and
unknown-tool errors returning proper JSON-RPC errors.

**Limits.** Iris is a tiny, famously easy dataset and 30 test rows is
a small sample — 1.000 test accuracy proves the pipeline, not that
this model generalises to harder data. The server is stdio-only (one
client, one process), has no auth, and the model is retrained from
scratch on every startup (~0.4 s), which is fine at this size and
would not scale to a large dataset.
