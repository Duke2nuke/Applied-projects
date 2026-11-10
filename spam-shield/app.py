"""Flask REST API serving the spam classifier.

Trains the model at startup from the hand-written dataset (fast: 60 short
texts), so no pickled model file is needed. Endpoints:
  GET  /health  -> {"status": "ok"}
  POST /predict {"text": "..."} -> {"text": ..., "label": "ham"|"spam",
                                     "spam_probability": 0.0-1.0}
"""

from flask import Flask, jsonify, request

from model import train_and_eval

app = Flask(__name__)
MODEL, METRICS = train_and_eval()


@app.get("/health")
def health():
    return jsonify({"status": "ok", "model": "tfidf-logreg-spam",
                    "test_accuracy": METRICS["accuracy"]})


@app.post("/predict")
def predict():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "Provide a non-empty 'text' field."}), 400
    proba = MODEL.predict_proba([text])[0]
    label = "spam" if int(proba[1] >= 0.5) else "ham"
    return jsonify({
        "text": text,
        "label": label,
        "spam_probability": round(float(proba[1]), 4),
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
