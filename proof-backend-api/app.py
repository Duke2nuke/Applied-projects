"""Tasks API — a small REST API with CRUD + token auth.

Stack: Python standard library + Flask, SQLite storage.
Local demo only — not production-ready (see README.md).
"""

import hashlib
import os
import secrets
import sqlite3

from flask import Flask, g, jsonify, request

app = Flask(__name__)

DB_PATH = os.environ.get("TASKS_DB", os.path.join(os.path.dirname(__file__), "tasks.db"))

# Demo user, seeded locally. Demo-only credentials — change in production.
# Username: demo / Password: demo1234
DEMO_USERNAME = "demo"
DEMO_PASSWORD_HASH = hashlib.sha256(b"demo1234").hexdigest()

# Tokens issued by /login, kept in memory (lost on restart — fine for a demo).
TOKENS = set()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title TEXT NOT NULL, "
            "description TEXT NOT NULL DEFAULT '', "
            "done INTEGER NOT NULL DEFAULT 0)"
        )
        g.db.commit()
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def task_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "done": bool(row["done"]),
    }


def error(message, status):
    return jsonify({"error": message}), status


def require_auth():
    """Return an error response when the request has no valid token, else None."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return error("missing or invalid Authorization header", 401)
    if auth[len("Bearer "):] not in TOKENS:
        return error("invalid token", 401)
    return None


def validate_task_payload(data, partial=False):
    """Validate a task payload. Returns (cleaned_dict, error_message or None)."""
    if not isinstance(data, dict):
        return None, "request body must be a JSON object"
    cleaned = {}
    if "title" in data or not partial:
        title = data.get("title")
        if not isinstance(title, str) or not title.strip():
            return None, "title is required and must be a non-empty string"
        cleaned["title"] = title.strip()
    if "description" in data:
        if not isinstance(data["description"], str):
            return None, "description must be a string"
        cleaned["description"] = data["description"]
    if "done" in data:
        if not isinstance(data["done"], bool):
            return None, "done must be a boolean"
        cleaned["done"] = data["done"]
    return cleaned, None


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/login")
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("request body must be a JSON object", 400)
    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return error("username and password are required", 400)
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if username != DEMO_USERNAME or password_hash != DEMO_PASSWORD_HASH:
        return error("invalid username or password", 401)
    token = secrets.token_hex(32)
    TOKENS.add(token)
    return jsonify({"token": token})


@app.get("/tasks")
def list_tasks():
    auth_error = require_auth()
    if auth_error is not None:
        return auth_error
    rows = get_db().execute("SELECT * FROM tasks ORDER BY id").fetchall()
    return jsonify([task_to_dict(row) for row in rows])


@app.post("/tasks")
def create_task():
    auth_error = require_auth()
    if auth_error is not None:
        return auth_error
    data = request.get_json(silent=True)
    cleaned, err = validate_task_payload(data)
    if err is not None:
        return error(err, 400)
    db = get_db()
    cur = db.execute(
        "INSERT INTO tasks (title, description, done) VALUES (?, ?, ?)",
        (cleaned["title"], cleaned.get("description", ""), int(cleaned.get("done", False))),
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(task_to_dict(row)), 201


@app.get("/tasks/<int:task_id>")
def get_task(task_id):
    auth_error = require_auth()
    if auth_error is not None:
        return auth_error
    row = get_db().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return error("task not found", 404)
    return jsonify(task_to_dict(row))


@app.put("/tasks/<int:task_id>")
def update_task(task_id):
    auth_error = require_auth()
    if auth_error is not None:
        return auth_error
    db = get_db()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return error("task not found", 404)
    data = request.get_json(silent=True)
    cleaned, err = validate_task_payload(data, partial=True)
    if err is not None:
        return error(err, 400)
    if not cleaned:
        return error("no fields to update", 400)
    current = task_to_dict(row)
    title = cleaned.get("title", current["title"])
    description = cleaned.get("description", current["description"])
    done = cleaned.get("done", current["done"])
    db.execute(
        "UPDATE tasks SET title = ?, description = ?, done = ? WHERE id = ?",
        (title, description, int(done), task_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return jsonify(task_to_dict(row))


@app.delete("/tasks/<int:task_id>")
def delete_task(task_id):
    auth_error = require_auth()
    if auth_error is not None:
        return auth_error
    db = get_db()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return error("task not found", 404)
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return jsonify({"deleted": task_id})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
