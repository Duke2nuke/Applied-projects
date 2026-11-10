# LOCAL EDUCATIONAL LAB — own code only, never run against real systems

# Fixes report — vulnerable app → fixed app

Lab only, localhost only. Never scan or test any real/external system.
Demo credentials only: `demo` / `password123` (demo-only, never real).

| # | Flaw in `app.py` | Line (approx.) | Fix in `fixed_app.py` |
|---|---|---|---|
| 1 | SQL injection — login query built with an f-string, so input becomes SQL | `login()`: `query = f"SELECT * ... '{username}' ..."` | Parameterised query: `SELECT username, password FROM users WHERE username = ?` with `(username,)` as a bound parameter. Input is data, never SQL. |
| 2 | Reflected XSS — `/greet` echoes `name` into the page unescaped | `greet()`: `return f"<h1>Hello, {name}!</h1>"` | `escape(name)` before echoing it, so `<script>` becomes `&lt;script&gt;` and is shown as text, not run. |
| 3 | Plaintext password storage — demo password stored as-is in SQLite | `init_db()`: `INSERT ... ("demo", "password123")` | Salted hash with `hashlib.pbkdf2_hmac("sha256", ..., salt, 100_000)`, stored as `salt_hex:hash_hex`. Login verifies with `verify_password()` (`hmac.compare_digest`); the plaintext is never stored or compared. |

## Scanner result

- Before patching (`app.py`): **3 flaws** — SQL injection, Reflected XSS, Plaintext password storage.
- After patching (`fixed_app.py`): **0 flaws** — verified by running `python audit.py` (see README for the real output).
