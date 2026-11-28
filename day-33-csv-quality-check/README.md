# Day 33 — dqcheck: CSV Data-Quality Checker (Day C: community / open-source)

A stdlib-only CLI that profiles a CSV file and flags the data-quality
problems that bite before training or analysis: missing values, constant
or fully-empty columns, duplicate rows, mixed types, outliers, invalid
emails and unparseable dates. One command, no dependencies, CI-friendly
exit codes.

## Who would use this, and why

Anyone who receives a CSV from somewhere else — a teammate, a client, a
scrape, an export — and has to decide whether it is safe to load. Data
scientists run this before training (a column that is 40% missing or a
duplicated row silently skews a model); data engineers run it in CI so a
bad upstream export fails the pipeline instead of corrupting a table;
open-source maintainers run it on example datasets shipped in a repo.
It answers "is this file clean?" in under a second, without pandas,
without a notebook, and without uploading the data anywhere.

## Install / run

Requires Python 3.9+. No third-party packages.

```bash
# text report, exit 0/1/2 for PASS / WARN / FAIL
python dqcheck.py data.csv

# machine-readable report
python dqcheck.py data.csv --json

# also fail the build on warnings (e.g. in CI)
python dqcheck.py data.csv --fail-on warn

# semicolon-delimited file, or a stricter missing-value threshold
python dqcheck.py data.csv --delimiter ";" --missing-threshold 0.1
```

Exit codes: `0` = PASS, `1` = WARN (only with `--fail-on warn`),
`2` = FAIL or a read error.

## What it checks

| Check | Severity | Rule |
| --- | --- | --- |
| Duplicate rows | error | exact full-row copies |
| Ragged rows | error | more fields than the header |
| Empty column | error | every cell missing |
| Mixed types | error | e.g. ints and strings in one column |
| High missing | warn | missing fraction above `--missing-threshold` (default 20%) |
| Constant column | warn | one value in every row |
| Outliers | warn | 1.5 x IQR rule, numeric columns only |
| Near-unique column | warn | > 95% distinct values, not an `*id*` column |
| Invalid email | warn | columns named `*email*`, simple `user@host.tld` check |
| Unparseable date | warn | columns named `*date*` that do not parse as dates |

Missing means blank or one of `NA`, `N/A`, `null`, `none`, `NaN`, `-`.

## Example

`example.csv` is a 12-row synthetic customer list with planted problems.
Running `python dqcheck.py example.csv` prints (see
`example_report.txt` for the full output):

```text
dqcheck 1.0.0 — example.csv
Rows: 12  Columns: 8  Missing cells: 14  Duplicate rows: 1
Verdict: FAIL (4 error(s), 4 warning(s))

Issues:
  ERROR duplicate_rows: 1 duplicate row(s) (1/12 rows are extra copies)
  ERROR [age] mixed_types: mixed value types: int x11, string x1
  WARN  [email] invalid_email: 1 value(s) are not valid emails, e.g. 'kabir[at]example.com'
  ERROR [signup_date] mixed_types: mixed value types: date x11, string x1
  WARN  [signup_date] bad_date: 1 value(s) do not parse as dates, e.g. 'not-a-date'
  WARN  [country] constant_column: constant value 'India' in every row — carries no information
  WARN  [currency] constant_column: constant value 'INR' in every row — carries no information
  ERROR [notes] empty_column: column is completely empty
```

So in one run it catches the duplicated Anaya row, the `"unknown"` age,
the `kabir[at]example.com` typo, the `not-a-date` signup date, the two
columns that carry no information, and the never-filled `notes` column.

## 2-minute explainer

**Problem:** CSVs arrive dirty — duplicated rows, half-empty columns, a
typo'd email, a date that isn't a date — and the failure shows up much
later, as a wrong model or a broken dashboard, when the cause is hard to
trace back to the file.

**Approach:** `dqcheck` reads the file once with `csv.DictReader`
(delimiter auto-detected), profiles every column (type inferred per
value, then collapsed: `int`/`float` to `number`, anything else mixed),
and applies a fixed set of checks with error/warn severities. Numeric
columns get min/max/mean/median/stdev and an IQR outlier count;
string columns get top values. The report is text by default and JSON
with `--json`, and the exit code is designed for CI gates.

**Results:** on the 12-row synthetic example it returns FAIL with
4 errors and 4 warnings, naming every planted problem (see above). On a
clean 12-row file it returns PASS with 0 issues. 14/14 tests pass
(`python -m unittest test_dqcheck -v`).

**Limits:** outlier detection only runs on columns whose values are all
numeric — a column with one stray string (like the `age` column's
`"unknown"`) is flagged as mixed-type instead, so the planted age of 250
is not separately called out as an outlier. Type inference is heuristic
(`"2026-01-05"` reads as a date, `"1"` as an int); a column of
zero-padded codes such as `"007"` will read as int. The email check is a
format check only — it never verifies that an address exists. It checks
one file at a time and reads the whole file into memory.

## Contributing

Issues and pull requests are welcome. Please keep it stdlib-only, add a
test for any new check in `test_dqcheck.py`, and run the suite before
submitting:

```bash
python -m unittest test_dqcheck -v
```

## Licence

MIT — see `LICENSE`.
