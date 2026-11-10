# Task App — Full Stack Proof Project

A small task/notes app, end to end: a Flask + SQLite backend API with
token auth, CRUD and input validation, plus a dependency-free vanilla
HTML/CSS/JS frontend that calls the API.

## What it does

- Log in with the demo account (`demo` / `demo123`) and get a bearer token.
- Create tasks with a title and optional notes, list them, mark them
  done/undone, and delete them. Tasks persist in a local SQLite file.
- The API validates input (non-empty title, length limits, `done` must be
  a boolean) and returns 400/401/404 with a JSON error message.

## How to run

```bash
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in a browser. One command starts both
parts: the same Flask server serves the API under `/api` and the
frontend at `/`.

The SQLite file `tasks.db` is created next to `app.py` on first run.
It is local data, not committed. Set `TASK_DB=/path/to/file.db` to use
a different location.

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | `{"status": "ok"}` |
| POST | `/api/login` | `{"username", "password"}` → `{"token"}` |
| GET | `/api/tasks` | List tasks (auth required) |
| POST | `/api/tasks` | `{"title", "notes?"}` → 201 (auth required) |
| PATCH | `/api/tasks/<id>` | `{"title?", "notes?", "done?"}` (auth required) |
| DELETE | `/api/tasks/<id>` | (auth required) |

Authenticated requests send `Authorization: Bearer <token>`.
Unauthenticated requests get 401.

## Tests

```bash
python test_e2e.py
```

Uses Flask's test client against a throwaway SQLite file. Checks the
frontend files serve and runs the full flow — login → create → list →
toggle → delete — plus unauthenticated (401), invalid-input (400) and
missing-task (404) cases. Prints PASS/FAIL per case and a final X/Y count.

**Result: 14/14 tests passed** (run locally, 2026-11-10, Flask 3.1.3).

## Honest limits

- Small demo project with demo data only; for local use.
- Demo auth only: one hard-coded demo account, tokens kept in memory
  and lost on restart, no password hashing, no HTTPS. Not
  production-ready and not a security model to copy.
- Single-user, single-process SQLite; no tests for concurrency or scale.
