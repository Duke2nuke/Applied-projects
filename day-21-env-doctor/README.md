# Env Doctor — Day 21 (Day C: community / open-source)

A stdlib-only CLI that audits a project's `.env` file against its
`.env.example` and tells you, in plain language, exactly why your app
will crash at startup — before it does.

## The problem

Every project ships a `.env.example` listing the variables the app
needs, and every developer has a local `.env` that slowly drifts out
of sync: a key is added to the example and nobody updates their
`.env`, a key is renamed, a value is left blank, a key is pasted
twice. The app then fails at runtime with a confusing error
(`KeyError: DATABASE_URL`) instead of failing fast with a clear list.

## What it does

    python env_doctor.py audit [--env .env] [--example .env.example]

Reports, per file pair:

- **MISSING** — keys in `.env.example` but not in `.env`
- **EXTRA** — keys in `.env` but not in the example (stale, or a typo)
- **EMPTY** — keys present but with no value
- **DUPLICATES** — the same key defined twice (the last one wins silently)
- **MALFORMED** — lines that are not `KEY=VALUE` at all

Exit code `1` when anything is missing, empty, duplicated or
malformed, so it works as a CI gate (`--strict` also fails on extra
keys). `--json` prints the report as JSON for scripts.

It also fixes the two common follow-ups:

    python env_doctor.py init   # generate .env.example from .env, values redacted
    python env_doctor.py fix    # append missing example keys (empty) to .env

`init` refuses to overwrite an existing `.env.example` that it did
not generate, so it cannot clobber a hand-written template.

Parsing handles `export ` prefixes, single/double-quoted values
(`#` inside quotes is kept), inline `# comments` on unquoted values,
and blank lines. It never prints a secret: reports list key names
only, and `init` writes keys with empty values.

## Example input / output

`example/.env` (demo values only, nothing real) vs
`example/.env.example`:

```
$ python env_doctor.py audit --env example/.env --example example/.env.example
env-doctor: example/.env vs example/.env.example
  4 keys in .env, 5 keys in .env.example
  MISSING (needed, not set):
    - REDIS_URL
  DUPLICATES (defined more than once):
    - DEBUG (lines 5, 6)
  MALFORMED LINES in .env:
    - line 7: 'MALFORMED LINE HERE'
```

## Who would use it, and why

Anyone who onboards onto a project, pulls a branch that adds a new
config variable, or runs CI: one command answers "is my local config
complete?" instead of discovering it from a runtime crash. It is the
check that belongs in a README's setup steps and in CI before tests
run — the same role `npm ls` or a lockfile check plays, for
environment config.

## Install / run

No dependencies — Python 3.8+ standard library only.

    git clone <this repo>
    cd day-21-env-doctor
    python env_doctor.py audit --env path/to/.env --example path/to/.env.example
    python -m unittest test_env_doctor -v

## Tests

11 tests pass (`python -m unittest test_env_doctor -v`): parsing
(quotes, `export`, inline comments, duplicates, malformed lines),
audit (missing / extra / empty, strict vs non-strict exit behaviour),
`init` (values redacted, refuses to overwrite a foreign example),
`fix` (appends missing keys, then audit is clean), and CLI exit codes
plus JSON output via subprocess.

## 2-minute explainer

**Problem:** `.env` files drift out of sync with `.env.example`, and
the failure shows up as a confusing runtime error instead of a clear
list of what is missing.

**Approach:** a small parser for the `.env` format (quotes, `export`,
inline comments, duplicate and malformed-line detection) plus a
set-difference audit between the two files, with three commands:
`audit` (report + CI exit code), `init` (generate a redacted example)
and `fix` (append missing keys).

**Results:** on the 7-line example pair it finds the one missing key
(`REDIS_URL`), the duplicated `DEBUG`, and the malformed line, and
exits 1; `fix` appends the missing key, which the audit then still
flags as EMPTY until a real value is filled in — the audit only goes
fully clean once values are set and the duplicate/malformed lines are
removed. 11/11 tests pass.

**Limits:** it checks key *presence*, not whether a value is valid
(a well-formed but wrong database URL still passes); it does not
validate values against a schema, resolve `${VAR}` references, or
check that the app actually reads every listed key. Those are
follow-ups, not claimed here.

## Open source

MIT licensed (see `LICENSE`). Contributions welcome: value validation
against a schema, `${VAR}` reference resolution, and a `--diff` mode
that shows which keys changed between two example files are the
obvious next issues.
