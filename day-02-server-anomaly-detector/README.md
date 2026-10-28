# Day 02 — Server Metrics Anomaly Detector (ML, Python)

Unsupervised anomaly detection on server metrics: can a small,
no-training-data method spot CPU spikes, latency spikes, memory
spikes, and request-rate collapses — without a fixed threshold that
breaks as soon as "normal" changes with the time of day?

## What it does

- Generates 14 days of hourly synthetic metrics (`generate.py`):
  CPU %, memory %, latency, requests/min, with a daily cycle plus
  noise, and 10 labelled injected anomalies. Synthetic data, clearly
  labelled — this is not real production telemetry.
- Detects anomalies (`detector.py`) in two steps:
  1. Remove the daily cycle: compare each hour with the median of
     the same hour on previous days (up to 7 days back).
  2. Score the residual robustly: modified z-score against the
     median/MAD of the previous 24 residuals. Flag if any metric
     exceeds 5.0.
- Reports precision/recall/F1 against the injected labels (`run.py`)
- Tests: `python -m unittest test_detector -v`

## Run it

```bash
pip install -r requirements.txt
python run.py
python -m unittest test_detector -v
```

## Results (measured by running `python run.py` on this machine)

- Rows: 336 (14 days, hourly) | Labelled anomalies: 10
- True positives: 10, false positives: 0, false negatives: 0
- Precision: 1.0, recall: 1.0, F1: 1.0
- The highest-scoring unlabelled point had max |z| = 4.5, just under
  the 5.0 threshold — so the separation is real on this data, but
  not by a wide margin.

Read that score honestly: it is perfect because this synthetic data
is clean — one big spike at a time, no gradual drift, no incidents
spanning many hours, no missing data. On real telemetry it would be
lower, and that is the interesting part to talk about (see Limits).

## 2-minute explainer (for interviews)

1. The problem with a fixed threshold ("alert if CPU > 90%") is that
   normal changes by time of day: 300 ms latency can be fine at peak
   and a symptom at 3 a.m. So first remove the daily cycle by
   comparing each hour with the same hour on previous days.
2. Then score what's left with a median/MAD modified z-score, not a
   mean/std z-score. A mean is dragged by the very spike you are
   trying to find; a median is not, so spikes stand out instead of
   hiding in their own average.
3. The first version of this detector used a trailing 24-hour window
   only, and got recall 0.5 — the daily cycle inflated the spread so
   spikes looked ordinary. Adding the same-hour baseline fixed it.
   That debugging story matters more than the final score: the
   method failed, the failure had a diagnosable cause, and the fix
   followed from the cause.
4. It is unsupervised: no labelled training data, no model file to
   ship. It flags points; a human still decides whether a flag is
   an incident.

## Limits

- Synthetic, single-spike anomalies only — no gradual leaks, no
  multi-hour incidents, no missing/corrupt data, no weekly cycle.
- Needs 72 hours of history before it can flag anything (48 hours
  for same-hour baselines, 24 more for residual spread), so it
  cannot protect a brand-new service.
- Flags a point, not a cause: it will not tell you *why* latency
  spiked, and correlated metrics can produce several flags for
  one underlying incident.
- Threshold 5.0 is a conventional robust-z cutoff, not a tuned
  guarantee — on noisier real data it would need re-checking
  against labelled incidents.
