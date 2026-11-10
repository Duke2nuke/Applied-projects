"""Flask API for seva-triage.

POST /triage    {"text": "..."} -> department, confidence, urgency, next step
GET  /analytics              -> department counts + urgency breakdown
GET  /health                  -> {"status": "ok"}
GET  /                        -> tiny HTML form for trying it out

The classifier retrains at startup from data.py (66 synthetic examples,
seconds) — no model file is committed.
"""

from collections import Counter

from flask import Flask, jsonify, request

from data import load_data
from model import SUGGESTED_NEXT_STEP, predict, train_full
from urgency import urgency

app = Flask(__name__)
MODEL = train_full()
TEXTS, LABELS = load_data()


@app.route("/")
def index():
    return """
    <h1>seva-triage</h1>
    <p>Routes a citizen grievance to the right department.</p>
    <form action="/triage" method="post" id="f">
      <textarea name="text" rows="4" cols="60"
        placeholder="e.g. There is no water supply in our street since yesterday"></textarea><br>
      <button type="submit">Triage</button>
    </form>
    <p>API: POST /triage with JSON {"text": "..."} &middot; GET /analytics &middot; GET /health</p>
    """


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/triage", methods=["POST"])
def triage():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or request.form.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    department, confidence = predict(MODEL, text)
    return jsonify(
        {
            "text": text,
            "department": department,
            "confidence": confidence,
            "urgency": urgency(text),
            "suggested_next_step": SUGGESTED_NEXT_STEP[department],
        }
    )


@app.route("/analytics")
def analytics():
    urgencies = Counter(urgency(t) for t in TEXTS)
    return jsonify(
        {
            "total_grievances": len(TEXTS),
            "department_counts": dict(sorted(Counter(LABELS).items())),
            "urgency_breakdown": {
                "high": urgencies.get("high", 0),
                "medium": urgencies.get("medium", 0),
                "low": urgencies.get("low", 0),
            },
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
