# NLP + Flask API — proof project

A text classifier served as a REST API: **TF-IDF + Logistic Regression**
(scikit-learn) behind a small **Flask** app, trained on 60 hand-written
messages (30 ham, 30 spam — synthetic, written for this project).

## What it proves

- **NLP**: text preprocessing, TF-IDF vectorisation, Logistic Regression classification.
- **REST API**: Flask app with `GET /health` and `POST /predict` returning a label and spam probability.
- **Evaluation**: precision / recall / F1 on a held-out split.

## Measured result

Run `python model.py` — real numbers, measured 10 Nov 2026 (15 held-out messages):

- **Accuracy: 1.0, macro F1: 1.0**
- Spam: precision 1.0, recall 1.0, F1 1.0
- Ham: precision 1.0, recall 1.0

## Run it

```bash
pip install -r requirements.txt
python model.py       # trains, prints metrics, writes metrics.json
python test_api.py    # health, /predict (spam + ham paraphrases), empty-input 400, metric checks
python app.py         # serves on http://127.0.0.1:5000
```

```bash
curl -X POST http://127.0.0.1:5000/predict \
  -H 'Content-Type: application/json' \
  -d '{"text": "You have won a free prize, click here to claim now."}'
# -> {"label": "spam", "spam_probability": ..., "text": "..."}
```

## Honest caveats

- **1.0 on 15 hand-written messages proves the pipeline works end to end, not real-world spam detection.** The messages are clean template-style text; real spam is messier and the model would score lower on it.
- The model trains at startup from `data.py` (60 short texts, seconds) — no pickled model file is committed.
- API tests use paraphrases that are *not* in the training set, so they test generalisation, not memorisation.
