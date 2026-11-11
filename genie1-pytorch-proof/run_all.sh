#!/bin/bash
# Reproduce the full GENIE1 local proof pipeline end to end (CPU, ~30 min).
# Run from work/:  bash run_all.sh
set -e
PY=.venv/bin/python
$PY train_ae.py
$PY train_cnn.py
$PY train_gnn.py
$PY train_contrastive.py
echo "ALL DONE — see outputs/*_metrics.json and results.md"
