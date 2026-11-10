# LOCAL EDUCATIONAL LAB — own code only, never run against real systems

# Ethical Hacking Lab — Proof Project (Lab Only)

> **LAB ONLY. LOCALHOST ONLY. Never scan or test any real or external system.**
> This project is a deliberately vulnerable demo app written by Aarambh
> for learning, plus a scanner and a patched version — all running only
> on his own machine, against his own local code. No real credentials
> anywhere: the only login is the demo-only `demo` / `password123`,
> labelled demo-only throughout. No port scanning, no brute-force
> tooling, no network calls outside localhost.

## What it does

- `app.py` — deliberately vulnerable Flask + SQLite demo app (binds
  `127.0.0.1` only, port 5000) with exactly 3 intentional flaws, each
  marked `# INTENTIONALLY VULNERABLE (lab)`:
  1. **SQL injection** in the login query (built with string formatting).
  2. **Reflected XSS** — unescaped user input echoed in `/greet`.
  3. **Plaintext password storage** in SQLite.
- `audit.py` — local scanner that reads **only** the `.py` files in
  this project folder and reports each flaw (file + line + type).
- `fixed_app.py` — patched copy: parameterised queries, HTML escaping,
  salted hashed passwords (`hashlib.pbkdf2_hmac`, 100,000 iterations).
  Binds `127.0.0.1` only, port 5001.
- `FIXES.md` — fixes report mapping each flaw to its patch.
- `test_lab.py` — tests proving the scanner finds 3 flaws in the
  vulnerable code, 0 in the fixed code, and that fixed login works
  with a hashed password.

## How to run (localhost only)

```bash
cd vuln-lab
python -m venv .venv && .venv/bin/pip install -r requirements.txt

# 1. Scan (before/after)
.venv/bin/python audit.py

# 2. Tests
.venv/bin/python test_lab.py

# 3. Run the vulnerable demo (localhost only, never expose it)
.venv/bin/python app.py        # http://127.0.0.1:5000  (demo / password123)

# 4. Run the fixed demo instead
.venv/bin/python fixed_app.py  # http://127.0.0.1:5001  (demo / password123)
```

Minimal local demo strings only (own app, localhost): e.g. SQLi demo
`' OR '1'='1' -- ` as the login username (any password) — it logs in
on the vulnerable app and fails on the fixed app; XSS demo
`<script>alert(1)</script>` in `/greet?name=`. These prove the flaws
in the own app and must never be used anywhere else.

## Real results (run locally, 2026-11-10)

Scanner — before patching: **3 flaws in `app.py`** (SQL injection,
Reflected XSS, Plaintext password storage); **0 flaws in
`fixed_app.py`**. See `audit.py` output when you run it.

Tests: **4/4 passing** — scanner finds 3 in vulnerable code, 0 in
fixed code, fixed login works with a hashed password (correct login
200, wrong password 401), fixed `/greet` escapes input.

Live localhost check (2026-11-10): vulnerable app — normal login
works, SQLi demo `' OR '1'='1' -- ` logs in as demo, XSS demo is
echoed raw (`<script>alert(1)</script>`); fixed app — normal login
works, same SQLi attempt returns 401, XSS demo is escaped
(`&lt;script&gt;`).
