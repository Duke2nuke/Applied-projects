# Tasks API — Backend Proof Project

A small REST API for managing tasks, built with Python (standard library +
Flask) and SQLite. This is the Backend proof project: it demonstrates CRUD,
token auth, and input validation in a real, tested API.

## What it does

- `GET /health` — health check, returns `{"status": "ok"}`.
- `POST /login` — log in with the demo user and get a token.
- `GET /tasks` — list all tasks (auth required).
- `POST /tasks` — create a task (auth required).
- `GET /tasks/<id>` — get one task (auth required).
- `PUT /tasks/<id>` — update a task (auth required).
- `DELETE /tasks/<id>` — delete a task (auth required).

Tasks have `id`, `title`, `description`, and `done`. Creating or updating
with an empty title, or with the wrong type for a field, returns `400` with a
JSON error message. Requests to `/tasks` without a valid token return `401`.
Unknown task ids return `404`.

Auth: send the token from `/login` as `Authorization: Bearer <token>`.

## Demo login

- Username: `demo`
- Password: `demo1234`

Demo-only credentials — change in production.

## How to run

```bash
# from this folder, using the shared venv
~/workspace/proof-projects-venv/bin/python app.py
# or: pip install -r requirements.txt, then: python app.py
```

The API listens on `http://127.0.0.1:5000`. A `tasks.db` SQLite file is
created in this folder on first run; it is local data and not committed.

Example:

```bash
curl http://127.0.0.1:5000/health
curl -X POST http://127.0.0.1:5000/login \
  -H 'Content-Type: application/json' \
  -d '{"username": "demo", "password": "demo1234"}'
# then, with the token:
curl http://127.0.0.1:5000/tasks -H 'Authorization: Bearer <token>'
curl -X POST http://127.0.0.1:5000/tasks \
  -H 'Authorization: Bearer <token>' -H 'Content-Type: application/json' \
  -d '{"title": "Write tests", "description": "for the API"}'
```

## How to test

```bash
~/workspace/proof-projects-venv/bin/python test_api.py
```

Uses Flask's test client against a temporary database. It exercises every
endpoint, including auth-failure and validation-failure cases, and prints
PASS/FAIL per case with a final count.

**Test result: 29/29 tests passed** (run 2026-11-10, locally).

## Honest limits

- Small demo project with a handful of hand-tested example tasks — not a
  production service.
- Local use only: no rate limiting, no HTTPS, no persistent sessions
  (tokens are kept in memory and lost on restart).
- Demo auth only: a single hard-coded demo user; do not use as-is in
  production.
