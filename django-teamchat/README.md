# TeamChat — Django + React team-chat proof

A small, working team-chat app built to learn the stack Zulip uses
(Python/Django backend + TypeScript/React frontend) and to anchor the
Django part of Aarambh's GSoC 2027 preparation. It is a proof project:
it proves he can build in Django + React, not that he has contributed
to Zulip or Django.

**Not affiliated with Zulip or Django.** Not a Zulip bot, not a Zulip
plugin, and no code from either project. Built from scratch on
11 Nov 2026 and published on GitHub the same day; never submitted
anywhere.

## What it does

- **Channels** — create a channel (e.g. `#general`, `#django`), list
  channels with message counts.
- **Messages** — post a message into a channel as a username, list a
  channel's thread in order.
- **Reactions** — react to a message with 👍 / ❤️ / 🎉; posting the
  same reaction again removes it (toggle). Counts aggregate per emoji.
- **Search** — search messages by content or author, optionally
  within one channel.
- **Simple login** — pick a username; the user is created on first
  use. No password, no tokens.
- **React frontend** — channel list, message thread, compose box,
  reaction buttons, search box, create-channel form.

## Stack

- Backend: Django 6.1.3 + Django REST Framework 3.18.3, SQLite,
  `django-cors-headers` for the local React dev server.
- Frontend: React 18 + TypeScript + Vite 5, Vitest + Testing Library.
- Files: `backend/` (Django project `teamchat`, app `chat`),
  `frontend/` (Vite app).

## How to run it

```bash
# 1. Backend (from the project root)
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py seed_demo   # 3 users, 3 channels, 7 messages
../.venv/bin/python manage.py runserver 127.0.0.1:8000

# 2. Frontend (new terminal, from the project root)
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Open http://localhost:5173, pick a username, and chat. The API is at
http://127.0.0.1:8000/api/ (e.g. `GET /api/channels/`,
`GET /api/messages/?search=django`).

## API (all JSON, no auth)

| Method | Endpoint | What it does |
|---|---|---|
| POST | `/api/login/` | `{"username": "aarambh"}` → user (creates on first use) |
| GET/POST | `/api/channels/` | List channels / create one |
| GET | `/api/channels/<id>/` | One channel |
| GET/POST | `/api/channels/<id>/messages/` | List / post messages |
| GET | `/api/messages/?search=<q>&channel=<id>` | Search messages |
| GET/POST | `/api/messages/<id>/reactions/` | List / toggle a reaction |
| GET | `/api/users/` | List users |

## Test results (verified 11 Nov 2026, locally)

- **Backend: 10/10 tests pass** — `cd backend && ../.venv/bin/python
  manage.py test chat` (0.7s). Covers login, channel create/list,
  duplicate-name rejection, posting/listing messages, empty-content
  and 404 errors, reaction toggle, reaction aggregation across users,
  and search by content and author.
- **Frontend: 2/2 tests pass** — `cd frontend && npm test` (Vitest +
  Testing Library, mocked API). Covers the login screen rendering,
  and loading the channel list + message thread with reactions after
  login.
- **Production build passes** — `npm run build` (tsc + Vite):
  33 modules, `dist/index.html` + 147.5 kB JS (47.6 kB gzip).
- **Live end-to-end check passed** — with both servers running:
  login 200, create channel 201, post message 201, search 1 hit,
  react 201, thread shows `{"🎉": 1}`; frontend preview served
  HTTP 200 and the CORS preflight allowed `http://localhost:5173`.

## Limits (honest)

- Local SQLite only; no Postgres, no deployment, no hosting.
- No real auth: anyone can post as any username, and there are no
  passwords, permissions, or private channels.
- No real-time updates: the thread refreshes on channel change, send,
  and react — no WebSockets / no live push (Zulip has real-time
  events; this does not).
- No message editing, deletion, threads, mentions, file uploads,
  or notifications.
- No Django admin password is set; create one with
  `manage.py createsuperuser` if you want to use `/admin/`.
- Seed data is 7 hand-written demo messages, not real chat history.

## What is still missing to demo it live

1. **A screen recording / screenshots** of the app running (login →
   channel → message → reaction → search) — not recorded yet.
2. **Hosting** — nothing is deployed; to show it to someone else it
   needs a host (e.g. Render/Railway for Django + a static host for
   the built frontend) and a real database + auth before it is shown
   as anything more than a local demo.
3. **Real-time** — WebSockets (Django Channels) if the demo is meant
   to show live messaging like Zulip.
4. **Push** — the repo was deliberately not pushed to GitHub in this
   build; pushing is a separate step for Aarambh to approve.
