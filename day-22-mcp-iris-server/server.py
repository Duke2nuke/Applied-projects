#!/usr/bin/env python3
"""Day 22 — MCP server exposing a trained Iris classifier as tools.

Stdlib-only Model Context Protocol server over stdio (newline-delimited
JSON-RPC 2.0), in the same style as Day 04's notes server but with a real
trained model behind the tools instead of CRUD notes.

Tools:
  predict_iris  — one flower (4 measurements) -> species + probabilities
  predict_batch — a list of flowers -> one prediction per flower
  model_info    — model card: classes, train/test sizes and accuracies

Run:  python3 server.py
Then send one JSON object per line on stdin (see README for examples).
No network, no API keys, no downloads: the model trains from the
data/iris.csv shipped in this folder at startup (~1 second).
"""

import json
import sys

from model import SPECIES, FEATURES, train_default, validate_features

SERVER_NAME = "mcp-iris-server"
SERVER_VERSION = "1.0.0"

TOOLS = [
    {
        "name": "predict_iris",
        "description": "Predict the Iris species for one flower from its "
                       "4 measurements (sepal_length, sepal_width, "
                       "petal_length, petal_width, in cm). Returns the "
                       "predicted species and a probability per species.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "measurements": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 4,
                    "maxItems": 4,
                    "description": "[sepal_length, sepal_width, "
                                   "petal_length, petal_width] in cm",
                }
            },
            "required": ["measurements"],
        },
    },
    {
        "name": "predict_batch",
        "description": "Predict the Iris species for a list of flowers. "
                       "Each item is a 4-measurement list, same order as "
                       "predict_iris. Returns one prediction per flower.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "samples": {
                    "type": "array",
                    "items": {"type": "array",
                              "items": {"type": "number"},
                              "minItems": 4, "maxItems": 4},
                    "description": "List of [sepal_length, sepal_width, "
                                   "petal_length, petal_width] lists.",
                }
            },
            "required": ["samples"],
        },
    },
    {
        "name": "model_info",
        "description": "Return the model card: classes, feature names, "
                       "train/test split sizes, train and test accuracy, "
                       "and training settings.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _text(payload):
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def main():
    clf, train, test = train_default()
    train_acc = clf.accuracy(train)
    test_acc = clf.accuracy(test)

    def call_tool(name, args):
        args = args or {}
        if name == "predict_iris":
            measurements = args.get("measurements")
            validate_features(measurements)
            probs = clf.predict_proba(measurements)
            return _text({
                "species": SPECIES[max(range(3), key=lambda c: probs[c])],
                "probabilities": {s: round(p, 4) for s, p in zip(SPECIES, probs)},
            })
        if name == "predict_batch":
            samples = args.get("samples")
            if not isinstance(samples, list):
                raise ValueError("samples must be a list of 4-measurement lists")
            out = []
            for s in samples:
                validate_features(s)
                probs = clf.predict_proba(s)
                out.append({
                    "species": SPECIES[max(range(3), key=lambda c: probs[c])],
                    "probabilities": {sp: round(p, 4) for sp, p in zip(SPECIES, probs)},
                })
            return _text({"predictions": out, "count": len(out)})
        if name == "model_info":
            return _text({
                "model": "softmax logistic regression (pure Python, stdlib only)",
                "classes": SPECIES,
                "features": FEATURES,
                "dataset": "Fisher's Iris, data/iris.csv (150 rows)",
                "train_size": len(train),
                "test_size": len(test),
                "train_accuracy": round(train_acc, 4),
                "test_accuracy": round(test_acc, 4),
                "epochs": clf.epochs,
                "learning_rate": clf.lr,
            })
        raise ValueError("unknown tool: %s" % name)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None,
                                         "error": {"code": -32700,
                                                   "message": "Parse error"}}) + "\n")
            sys.stdout.flush()
            continue
        req_id = req.get("id")
        method = req.get("method")
        if method == "notifications/initialized":
            continue  # notification: no reply
        try:
            if method == "initialize":
                result = {"protocolVersion": "2024-11-05",
                          "capabilities": {"tools": {}},
                          "serverInfo": {"name": SERVER_NAME,
                                         "version": SERVER_VERSION}}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                params = req.get("params") or {}
                result = call_tool(params.get("name"), params.get("arguments"))
            else:
                raise ValueError("unknown method: %s" % method)
            resp = {"jsonrpc": "2.0", "id": req_id, "result": result}
        except (ValueError, KeyError, TypeError) as e:
            resp = {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32602, "message": str(e)}}
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
