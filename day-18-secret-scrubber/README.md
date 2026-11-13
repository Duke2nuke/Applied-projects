# Day 18 — Secret Scrubber (Day C: community / open-source)

A small command-line tool that redacts secrets from text and log files
**before you share them** — paste a log into a GitHub issue, a support
ticket, or a chat message without leaking the API key that was in it.
Python standard library only, no dependencies, no installation beyond
Python itself.

## Who would use this, and why

Anyone who has ever pasted a log, a config dump, or a crash report
somewhere public and then realised — too late — that it contained a
live credential. It happens to everyone: debug logging prints the
full request, an error message includes the database URL, a CI log
echoes an environment variable. Existing answers are either manual
eyeballing (unreliable at 2am, and you cannot un-paste a secret) or
heavyweight secret-scanning suites built for CI pipelines. This is
the middle ground: one readable script you run on the file *before*
you share it, with a report that says what it found — by type, never
including the secret itself — and a `--check` mode that fails CI if
a secret is present.

Open-source framing: MIT licensed (see `LICENSE`), contributions
welcome — good first issues would be a `--mask` mode that keeps the
last 4 characters (e.g. `AKIA...EXAMPLE`), a `--diff` mode that
shows only the changed lines, and new built-in patterns (e.g.
OpenAI `sk-` keys, Stripe keys) with tests. Issues and pull
requests that keep the tool stdlib-only and never print a secret
value are in scope.

## What it redacts (built-in patterns)

| Type | Example format caught |
|---|---|
| `AWS_ACCESS_KEY` | `AKIA...` (20 chars) |
| `AWS_SECRET_KEY` | `aws_secret_access_key = ...` (40 chars) |
| `GITHUB_TOKEN` | `ghp_...`, `gho_...`, `github_pat_...` |
| `SLACK_TOKEN` | `xoxb-...`, `xoxp-...`, etc. |
| `JWT` | `eyJ...eyJ....` (three-part token) |
| `BEARER_TOKEN` | `Authorization: Bearer ...` (scheme kept) |
| `URL_PASSWORD` | `postgres://user:password@host` (user + host kept) |
| `GENERIC_SECRET` | `api_key = "..."`, `password: ...` (key name kept) |
| `PRIVATE_KEY_BLOCK` | `-----BEGIN ... PRIVATE KEY-----` (whole block) |

Opt-in with flags: `--include-email` (email addresses),
`--include-cards` (Luhn-valid card-like numbers only — a
16-digit reference number that fails the Luhn check is left alone).

Deliberately **not** redacted: placeholder values such as
`your-key-here`, `***`, `${API_TOKEN}`, or `<paste-key-here>`, so
tutorials and templates stay clean. Scrubbing is idempotent:
running the tool on its own output changes nothing.

## Install / run

No installation — Python 3.8+ only:

```bash
python3 secret_scrubber.py app.log                    # scrub to stdout
cat app.log | python3 secret_scrubber.py > clean.log  # stdin -> stdout
python3 secret_scrubber.py --in-place app.log         # rewrite, keep app.log.bak
python3 secret_scrubber.py --output clean.log app.log
python3 secret_scrubber.py --check app.log            # exit 1 if any secret found
python3 secret_scrubber.py --report report.json app.log
python3 secret_scrubber.py --config patterns.json app.log   # your own patterns
python3 secret_scrubber.py --list-patterns
```

A custom-patterns config is JSON:

```json
{"patterns": [{"name": "INTERNAL_ID", "regex": "\\bINT-[0-9]{6}\\b"}]}
```

## Example

Input — `example/leaky.log` (synthetic log; every secret in it is a
**fake**, hand-made example value, clearly labelled in the file):

```
2026-11-13 09:02:13 DEBUG aws key in use: AKIAIOSFODNN7EXAMPLE
2026-11-13 09:02:14 DEBUG github token: ghp_Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0Uv1Wx2
2026-11-13 09:02:17 ERROR db connect failed: postgres://appuser:s3cretPass9@db.internal:5432/app
2026-11-13 09:02:18 DEBUG api_key = "sk-fake-key-for-testing-123456"
```

Output — `example/leaky.log.scrubbed` (run it yourself with
`python3 secret_scrubber.py example/leaky.log`):

```
2026-11-13 09:02:13 DEBUG aws key in use: [REDACTED:AWS_ACCESS_KEY]
2026-11-13 09:02:14 DEBUG github token: [REDACTED:GITHUB_TOKEN]
2026-11-13 09:02:17 ERROR db connect failed: postgres://appuser:[REDACTED:URL_PASSWORD]@db.internal:5432/app
2026-11-13 09:02:18 DEBUG api_key = "[REDACTED:GENERIC_SECRET]"
```

Measured on the full 13-line example log: **6 redactions across 6
lines** — one each of AWS key, GitHub token, Slack token, Bearer
token, URL password, and generic secret. The email on line 12 is
left alone by default (needs `--include-email`). The `--report`
JSON counts redactions by type and never contains a secret value.

## Tests

```bash
python3 -m unittest test_secret_scrubber -v
```

**19/19 tests pass.** They cover every built-in pattern, the
placeholder exceptions, the Luhn check (a real test-card number is
redacted, a random 16-digit number is not), report contents,
`--check` exit codes, `--in-place` backups, custom config patterns,
and idempotency (scrubbing scrubbed output is a no-op).

## Limits — read this before trusting it

- **Pattern matching, not understanding.** It catches known secret
  formats; a novel or custom token format will slip through unless
  you add it via `--config`. It is a safety net, not a guarantee.
- **False positives are possible.** The generic `key = value`
  pattern redacts any 8+ character value after a key-like name,
  including a harmless one. Check the report, not just the output.
- **It cannot un-leak a secret.** If a credential was already pasted
  somewhere unredacted, rotate it — scrubbing the local copy does
  not revoke the exposed one.
- **Binary files are not supported** — text (UTF-8) only.
- The report counts redactions; it does not list what was redacted,
  by design.

## 2-minute interview explainer

**Problem:** developers paste logs and config dumps into public
places — GitHub issues, support tickets, chat — and those dumps
routinely contain live credentials, because debug logging prints
full requests and error messages include database URLs. Once
pasted, a secret is compromised; eyeballing a 500-line log before
sharing is unreliable.

**Approach:** a single stdlib-only Python CLI. I defined the secret
formats as an ordered list of regex patterns — specific formats
first (AWS keys, GitHub/Slack tokens, JWTs, private-key blocks) so
a token gets its real label, generic `key = value` assignments
last. Group-mode patterns keep the useful context (the key name,
`Bearer`, the database user and host) and redact only the secret
part. Placeholders like `your-key-here` or `${API_TOKEN}` are
explicitly exempted, card-like numbers must pass a Luhn check, and
the tool is idempotent — re-scrubbing its own output changes
nothing. Three modes cover the real workflows: stdout for a quick
check, `--in-place` with a `.bak` backup, and `--check` for CI,
plus a JSON report that counts redactions by type without ever
containing a secret value.

**Results:** on the 13-line synthetic example log it makes 6
redactions across 6 lines, one of each type, and 19/19 unit tests
pass — every pattern, the placeholder exceptions, the Luhn
validation, check-mode exit codes, in-place backups, custom
patterns from a JSON config, and idempotency.

**Limits:** it is pattern matching, not understanding — a novel
token format slips through unless added via config, the generic
pattern can over-redact a harmless value, and it cannot un-leak a
credential that was already pasted; that one has to be rotated.
