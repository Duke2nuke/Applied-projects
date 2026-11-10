# LOCAL EDUCATIONAL LAB — own code only, never run against real systems
"""Patched version of the lab demo app (LAB ONLY).

LOCAL EDUCATIONAL LAB — own code only, never run against real systems.
Binds to 127.0.0.1 only. Demo credentials only: demo / password123
(labelled demo-only, never a real credential).

Fixes, one per flaw in app.py (see FIXES.md):
  1. Parameterised queries — user input is never part of the SQL string.
  2. HTML escaping — user input is escaped before it is echoed.
  3. Salted hashed passwords — hashlib.pbkdf2_hmac, never plaintext.
"""
import hashlib
import hmac
import os
import sqlite3
from pathlib import Path

from flask import Flask, request
from markupsafe import escape

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "lab_fixed.db"


def hash_password(password, salt=None):
    """Return 'salt_hex:hash_hex' using PBKDF2-HMAC-SHA256."""
    salt = salt if salt is not None else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password, stored):
    """Check a password against a stored 'salt_hex:hash_hex' value."""
    try:
        salt_hex, hash_hex = stored.split(":")
    except ValueError:
        return False
    expected = hash_password(password, salt=bytes.fromhex(salt_hex))
    return hmac.compare_digest(expected, stored)


def init_db(db_path=None):
    """Create the local demo database with one demo-only user (hashed)."""
    path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users "
        "(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)"
    )
    # Demo-only value "password123", stored only as a salted hash.
    stored_hash = hash_password("password123")
    conn.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", ("demo", stored_hash))
    conn.commit()
    conn.close()


def get_user(username):
    """Fetch a user by name with a parameterised query."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username, password FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row


@app.route("/")
def home():
    return (
        "<h1>Local Educational Lab — fixed demo (own code only)</h1>"
        "<p>Demo login: demo / password123 (demo-only).</p>"
        "<ul><li>POST /login</li><li>GET /greet?name=...</li></ul>"
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return (
            '<form method="post">'
            'Username: <input name="username"><br>'
            'Password: <input name="password" type="password"><br>'
            '<input type="submit" value="Log in"></form>'
        )
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    row = get_user(username)
    if row and verify_password(password, row[1]):
        return f"<h1>Logged in as {escape(row[0])}</h1>"
    return "<h1>Login failed</h1>", 401


@app.route("/greet")
def greet():
    name = request.args.get("name", "guest")
    return f"<h1>Hello, {escape(name)}!</h1>"


if __name__ == "__main__":
    init_db()
    # Localhost only.
    app.run(host="127.0.0.1", port=5001, debug=False)
