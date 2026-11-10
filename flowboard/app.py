"""Task/notes app — Flask + SQLite backend API with a vanilla JS frontend.

Demo auth only: a single demo account (demo / demo123) that returns a
random bearer token on login. Local use only — not production-ready:
no password hashing, no HTTPS, tokens live only in memory, and the
SQLite file is created next to this file on first run (not committed).
"""
import os
import secrets
import sqlite3

from flask import Flask, g, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static", static_url_path="/static")

DB_PATH = os.environ.get("TASK_DB", os.path.join(os.path.dirname(__file__), "tasks.db"))

# Demo credentials, documented in the README. Local demo only.
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo123"

# token -> username, in memory only; tokens die when the server restarts.
TOKENS = {}

MAX_TITLE_LEN = 200
MAX_NOTES_LEN = 2000


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            done INTEGER NOT NULL DEFAULT 0
        )"""
    )
    db.commit()
    db.close()


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


init_db()


def task_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "notes": row["notes"],
        "done": bool(row["done"]),
    }


def require_auth():
    """Return an error response (or None) for a missing/invalid token."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing or invalid Authorization header"}), 401
    token = auth[len("Bearer "):].strip()
    if token not in TOKENS:
        return jsonify({"error": "invalid or expired token"}), 401
    return None


def validate_task_payload(data):
    """Return (title, notes, error_response)."""
    if not isinstance(data, dict):
        return None, None, (jsonify({"error": "request body must be a JSON object"}), 400)
    title = data.get("title")
    notes = data.get("notes", "")
    if not isinstance(title, str) or not title.strip():
        return None, None, (jsonify({"error": "title is required and must be a non-empty string"}), 400)
    if len(title.strip()) > MAX_TITLE_LEN:
        return None, None, (jsonify({"error": f"title must be at most {MAX_TITLE_LEN} characters"}), 400)
    if not isinstance(notes, str):
        return None, None, (jsonify({"error": "notes must be a string"}), 400)
    if len(notes) > MAX_NOTES_LEN:
        return None, None, (jsonify({"error": f"notes must be at most {MAX_NOTES_LEN} characters"}), 400)
    return title.strip(), notes, None


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    if data.get("username") == DEMO_USERNAME and data.get("password") == DEMO_PASSWORD:
        token = secrets.token_hex(16)
        TOKENS[token] = DEMO_USERNAME
        return jsonify({"token": token, "username": DEMO_USERNAME})
    return jsonify({"error": "invalid username or password"}), 401


@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    err = require_auth()
    if err:
        return err
    rows = get_db().execute("SELECT * FROM tasks ORDER BY id").fetchall()
    return jsonify([task_to_dict(r) for r in rows])


@app.route("/api/tasks", methods=["POST"])
def create_task():
    err = require_auth()
    if err:
        return err
    title, notes, validation_err = validate_task_payload(request.get_json(silent=True))
    if validation_err:
        return validation_err
    db = get_db()
    cur = db.execute("INSERT INTO tasks (title, notes) VALUES (?, ?)", (title, notes))
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(task_to_dict(row)), 201


@app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
def update_task(task_id):
    err = require_auth()
    if err:
        return err
    db = get_db()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return jsonify({"error": "task not found"}), 404
    data = request.get_json(silent=True) or {}
    title, notes = row["title"], row["notes"]
    done = bool(row["done"])
    if "title" in data or "notes" in data:
        new_title, new_notes, validation_err = validate_task_payload(
            {"title": data.get("title", title), "notes": data.get("notes", notes)}
        )
        if validation_err:
            return validation_err
        title, notes = new_title, new_notes
    if "done" in data:
        if not isinstance(data["done"], bool):
            return jsonify({"error": "done must be true or false"}), 400
        done = data["done"]
    db.execute(
        "UPDATE tasks SET title = ?, notes = ?, done = ? WHERE id = ?",
        (title, notes, int(done), task_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return jsonify(task_to_dict(row))


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    err = require_auth()
    if err:
        return err
    db = get_db()
    row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return jsonify({"error": "task not found"}), 404
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return jsonify({"deleted": task_id})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
