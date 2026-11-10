# Habit Tracker — Frontend proof project

A small interactive habit / workout tracker. A demo app built with vanilla
TypeScript + HTML/CSS — no framework, no build chain beyond the TypeScript
compiler, no backend, no account.

## What it does

- **Add / edit / delete habits** — name, category (Workout / Health / Study /
  Other), and a weekly target (1–7 days per week).
- **Mark done today** — one click toggles today's completion on or off.
- **Progress summary** — total habits, habits done today, completions this
  week, and best current streak.
- **Streaks** — consecutive completed days counting back from today. If today
  isn't ticked off yet, the streak counts back from yesterday, so it isn't
  broken just because today hasn't been done yet.
- **Weekly count + progress bar** — completions in the current Monday–Sunday
  week against the habit's target.
- **Filter / search** — free-text search over name and category, plus a
  category filter.
- **Persistence** — habits are saved to `localStorage` in this browser only
  (`habit-tracker-habits-v1`). Reload the page and they are still there.
  First visit shows two sample habits so the streak and weekly counts are
  visible; "Reset demo data" restores them, "Clear all" removes everything.

## Honest limits

- Small demo app. Data lives only in this browser's localStorage; clearing
  browser data deletes it. There is no backend, no sync, no login.
- Streaks and weekly counts use the browser's local calendar date.
- Works fully offline from local files — no CDN, no external fonts, no
  network calls at all.

## Run it in a browser

```bash
cd proof-frontend-app
python3 -m http.server 8000
```

Then open <http://localhost:8000> in any modern browser.

(Opening `index.html` directly with `file://` also works in most browsers,
but a local server is the reliable route for ES modules.)

### What to verify by hand

1. The page loads with two sample habits and a summary showing 2 habits.
2. Click "Mark done today" on a habit — its weekly count and the summary's
   "done today" number go up; click again and they go back down.
3. Add a habit ("Test run", Workout, 3/week) — it appears in the list and
   survives a page reload.
4. Type "read" in Search — only the reading habit stays visible; clear it
   and all habits return.
5. Pick "Workout" in the category filter — only workout habits stay visible.
6. Click Edit on a habit, change its name, Save — the new name shows.
   Delete removes it after a confirmation.
7. Reload the page — everything you changed is still there (localStorage).

## Files

| File | What it is |
| --- | --- |
| `index.html` | Page structure, loads `app.js` as an ES module |
| `styles.css` | All styling, plain CSS, system font stack |
| `logic.ts` | Pure habit logic — no DOM, no storage, no network |
| `app.ts` | Browser UI layer over `logic.ts`; owns localStorage |
| `logic.js` / `app.js` | Compiled output of the `.ts` files (committed so the app runs without a build step) |
| `test_frontend.js` | Node tests for the compiled `logic.js` |
| `tsconfig.json` | TypeScript config (`strict`, ES2020, ES modules) |
| `package.json` | `"type": "module"`, `build` / `test` scripts |

## Build (recompile the TypeScript)

```bash
npm run build
```

This runs the TypeScript compiler (version 7.0.2, fetched via npx). Note:
plain `npx tsc` on this machine resolves to an unrelated deprecated `tsc`
package, so the build uses `npx -y typescript` instead — that is the
TypeScript compiler's own binary.

## Tests (run for real, 10 Nov 2026)

```bash
node test_frontend.js
```

**Result: 29/29 tests passed**, exit code 0. The tests run against the
compiled `logic.js` in Node with no browser, and cover: create/add/update/
delete (including invalid names and unknown ids), toggle on/off, invalid
dates, streaks (4-day run, counting from yesterday, gap breaks it, none,
stale), weekly counts (previous-week completions excluded), filter/search
(name, category, no-match), the weekly summary totals, and `parseHabits`
(malformed / wrong-shaped / valid JSON).

An HTTP smoke check also passed: `index.html`, `app.js`, `logic.js`, and
`styles.css` all served with HTTP 200 from `python3 -m http.server`.
