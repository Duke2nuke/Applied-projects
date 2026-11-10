# LOCAL EDUCATIONAL LAB — own code only, never run against real systems
"""Deliberately vulnerable demo app (LAB ONLY).

LOCAL EDUCATIONAL LAB — own code only, never run against real systems.
Binds to 127.0.0.1 only. Demo credentials only: demo / password123
(labelled demo-only, never a real credential). Do NOT deploy this app,
do NOT expose it on a network, and do NOT use it against any real system.

Contains exactly 3 intentional flaws, each marked
"# INTENTIONALLY VULNERABLE (lab)":
  1. SQL injection in the login query (string formatting).
  2. Reflected XSS — unescaped user input echoed into a page.
  3. Passwords stored in plaintext.
See fixed_app.py / FIXES.md for the patched version.
"""
import sqlite3
from pathlib import Path

from flask import Flask, request

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "lab.db"


def init_db(db_path=None):
    """Create the local demo database with one demo-only user."""
    path = Path(db_path) if db_path else DB_PATH
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users "
        "(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)"
    )
    # INTENTIONALLY VULNERABLE (lab): plaintext password storage.
    # Demo-only value "password123" — never a real credential.
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
        ("demo", "password123"),
    )
    conn.commit()
    conn.close()


@app.route("/")
def home():
    return (
        "<h1>Local Educational Lab — vulnerable demo (own code only)</h1>"
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # INTENTIONALLY VULNERABLE (lab): SQL injection — query built with
    # string formatting, so user input becomes part of the SQL.
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    row = cursor.fetchone()
    conn.close()
    if row:
        return f"<h1>Logged in as {row[1]}</h1>"
    return "<h1>Login failed</h1>", 401


@app.route("/greet")
def greet():
    name = request.args.get("name", "guest")
    # INTENTIONALLY VULNERABLE (lab): reflected XSS — user input echoed
    # into the page with no HTML escaping.
    return f"<h1>Hello, {name}!</h1>"


if __name__ == "__main__":
    init_db()
    # Localhost only. Never bind this vulnerable app to 0.0.0.0.
    app.run(host="127.0.0.1", port=5000, debug=False)
