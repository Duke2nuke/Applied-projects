# LogLens — Day 15 (Day C: community / open-source)

A small, dependency-free CLI that turns a raw log file into a readable
summary in seconds. Point it at a web-server access log (Apache/Nginx
combined format, with an optional trailing response-time field) or a
plain-text application log and it reports:

- total lines, and how many parsed as access lines, plain log lines,
  or nothing at all
- status-code breakdown by class (2xx / 3xx / 4xx / 5xx) and the
  error rate
- most-requested paths and most-active client IPs
- which paths produce the most 4xx/5xx errors
- slowest requests (when a response-time field is present)
- ERROR / WARN / INFO counts and the actual error lines, for app logs

## Who would use this, and why

Anyone who has ever SSH'd into a small server, a VPS, or a friend's
side project and stared at a 200,000-line `access.log` wondering
"what broke, and where?" — without installing an observability stack.
LogLens answers the first three questions in one command: what is
erroring, who is hitting it, and what is slow. It is stdlib-only, so
it runs anywhere Python 3.10+ exists, on logs of any size that fit in
memory for the top-N lists (counters only — the file is streamed).

## Install / run

```bash
python log_analyzer.py example/access.log
python log_analyzer.py example/app.log --top 5
python log_analyzer.py access.log --json report.json
python log_analyzer.py app.log --errors-only   # only the ERROR lines
```

No dependencies — `requirements.txt` is intentionally empty.
Python 3.10+ (uses `X | None` type syntax).

## Example

Input — `example/access.log` (synthetic, hand-written demo data):

```
203.0.113.7 - - [10/Nov/2026:08:00:09 +0530] "GET /api/reports?month=10 HTTP/1.1" 500 210 "-" "curl/8.0" 1.284
192.0.2.55 - - [10/Nov/2026:08:00:06 +0530] "GET /old-page HTTP/1.1" 404 151 "-" "Mozilla/5.0" 0.004
...
```

Output (actually run, 12 synthetic lines):

```
LogLens report — 12 lines
  access lines: 12  plain log lines: 0  unparsed: 0
  error rate (4xx+5xx): 58.3%
  status codes:
    200: 5
    401: 2
    404: 4
    500: 1
  top 10 paths:
        3  /old-page
        2  /api/users
        2  /api/login
        2  /api/reports?month=10
  paths with most errors:
        3  /old-page
        2  /api/login
        1  /api/reports?month=10
  slowest requests (seconds):
      1.284s  GET /api/reports?month=10 -> 500
      0.872s  GET /api/reports?month=10 -> 200
```

Input — `example/app.log` (synthetic):

```
2026-11-10 08:00:04 ERROR database connection lost, retrying (attempt 1/3)
2026-11-10 08:00:06 ERROR unhandled exception in /api/reports: division by zero
```

`--errors-only` prints exactly those two lines, with their line numbers.

## Tests

11 tests, all passing (run without pytest — the runner in the test
file's docstring also works with plain `python`):

```bash
python -m pytest test_log_analyzer.py -v   # if pytest is installed
```

They cover access-line parsing (fields, rejection of garbage),
plain-log level detection, status breakdown and error rate, top-N
paths/IPs/error paths, slowest-request ordering, mixed files with
unparsed lines, JSON serialisability, the CLI on both example files,
and the exit code for a missing file.

## Results (on the synthetic examples)

- `example/access.log`: 12/12 lines parsed, error rate 58.3%
  (4× 404 on `/old-page`, 2× 401 on `/api/login`, 1× 500 on
  `/api/reports?month=10`); slowest request 1.284 s, also the 500.
- `example/app.log`: 8/8 lines parsed — 2 ERROR, 1 WARN, 4 INFO,
  1 DEBUG; both error lines recovered with line numbers.

## Limits

- Only the combined access-log format is parsed (plus an optional
  trailing response time); custom log formats and JSON logs are not.
- Query strings are kept as part of the path, so
  `/api/reports?month=10` and `/api/reports?month=11` count
  separately — strip them first if you want per-endpoint totals.
- Plain-log detection is level-keyword based (`ERROR`, `WARN`,
  `INFO`, ...); a line with no level keyword counts as unparsed.
- Top-N lists are held in memory; the file itself is streamed, so
  very large logs are fine, but a log with millions of distinct
  paths will use proportional memory.

## 2-minute explainer

**Problem:** after a deploy, the first question is always "what just
broke?" — but the answer is buried in a raw log file, and setting up
real observability for a side project is overkill.

**Approach:** one stdlib-only Python script, no dependencies. A regex
parses each combined-format access line into IP, method, path, status,
size and optional response time; a second pass detects log levels in
plain-text app logs. Everything is counted with `collections.Counter`
while the file streams, then the report prints status classes, the
error rate, top paths and IPs, the paths producing the most errors,
the slowest requests, and the actual error lines. `--json` writes the
same report for scripting, `--errors-only` prints just the errors.

**Results:** on the 12-line synthetic access log it finds a 58.3%
error rate, names `/old-page` as the worst offender (3× 404), and
flags the 1.284 s request that returned a 500 — the three facts you
need before opening the code. On the synthetic app log it recovers
both error lines with line numbers.

**Limits:** combined format only, no JSON logs, query strings are
part of the path, and level detection is keyword-based — so it is a
first-look triage tool, not a replacement for structured logging.

## Licence & contributing

MIT licensed — see `LICENSE`. Contributions welcome: the most useful
next steps are a `--strip-query` flag, JSON-log support, and a
`--since/--until` time filter. Open an issue or a PR with a test
for any new parser behaviour.
