# seva-triage — Citizen Grievance Triage for e-Governance

A text classifier + analytics API that routes a citizen's grievance to the
right government department and flags how urgent it is. Built as a
proof-of-concept for e-governance work — the kind of applied AI/ML and
Data Analytics project the NIC Digital India Internship lists under its
areas (Artificial Intelligence and Machine Learning, Data Analytics,
Chatbot).

Example: *"No water for three days in our colony, please send a water
tanker"* → **Water Supply**, confidence 0.33, urgency **high**.

## What it does

- **Routing (ML):** TF-IDF + Logistic Regression (scikit-learn) classifies
  grievance text into 6 departments: Water Supply, Electricity,
  Roads & Transport, Health, Education, Revenue & Certificates.
- **Urgency (transparent rules, not ML):** a short explicit phrase list in
  `urgency.py`. High = health/safety risk or multi-day loss of a basic
  service (`burst`, `sewage`, `contaminated`, `hospital`, `ambulance`,
  `accident`, `outbreak`, `no water for`, …). Medium = long delays and
  blockages (`pending for`, `delayed`, `cancelled`, `blocked`,
  `waterlogged`, …). Everything else is low. Any officer can read the
  rules and see exactly why a grievance was flagged.
- **Analytics:** department-wise counts and urgency breakdown
  (`GET /analytics`).
- **API (Flask):** `POST /triage` returns department, confidence,
  urgency and a suggested next step; `GET /analytics`, `GET /health`,
  and a tiny HTML form at `GET /`.

## Dataset

66 hand-written synthetic grievances (11 per department) in `data.py`.
No real citizen data, no scraped data, no government records. A few
examples deliberately overlap departments (e.g. a power cut that stops
the water pump), because real grievances do that too.

## Measured results

Run `python train.py` — real numbers, measured 11 Nov 2026 on this
machine. Stratified split: 49 train / 17 held-out, `random_state=42`.

- **Accuracy: 0.8235** (14/17 held-out)
- **Macro F1: 0.825**
- Per-department F1: Water Supply 0.80, Electricity 0.80,
  Roads & Transport 0.80, Health 0.75, Education 0.80,
  Revenue & Certificates 1.00
- Urgency breakdown of the 66 synthetic grievances: high 17, medium 19,
  low 30 (see `metrics.json` and `GET /analytics`)

## Run it

```bash
pip install -r requirements.txt
python train.py                                  # trains, prints metrics, writes metrics.json
python -m unittest discover -s tests            # 15 tests
python app.py                                    # serves on http://127.0.0.1:5000
```

```bash
curl -X POST http://127.0.0.1:5000/triage \
  -H 'Content-Type: application/json' \
  -d '{"text": "No water for three days in our colony, please send a tanker"}'
# -> {"department": "Water Supply", "confidence": 0.3345, "urgency": "high",
#     "suggested_next_step": "Forward to the municipal water supply engineer; ..."}
```

## Tests

15 tests, all passing: classifier on paraphrases **not** in the training
set (so they test generalisation, not memorisation), the urgency rules
(high / medium / low), and the API (`/triage` fields + high-urgency
case, empty-text 400, `/analytics` counts, `/health`).

## Honest limits

- **0.82 accuracy on 17 hand-written synthetic grievances proves the
  pipeline works end to end, not real-world grievance routing.** The
  examples are clean template-style text; real grievances are messier,
  multilingual, and often span departments — the model would score
  lower on them.
- The model retrains at startup from `data.py` (seconds) — no pickled
  model file is committed.
- Urgency is keyword rules, not judgement: it flags phrases, it does
  not understand severity.
- **Not affiliated with NIC or any government body, and no real
  grievances were used.** This is a learning/proof-of-concept project
  only — not production-ready, not a deployed public service.
