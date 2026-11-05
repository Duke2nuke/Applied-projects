# Day 07 — Agent-Run Cost & Eval Analyser (Day A: trending-skill build)

A stdlib-only Python CLI that turns agent run logs (JSON Lines) into
the comparison agent teams actually care about: **cost per solved
task**, success rate, cache hit rate, and tokens per solved task —
per harness. It answers "which harness is cheapest per job actually
finished?", not "which model tops a leaderboard?".

## The trend this builds with

**Agent harness engineering + AI evals + cost-per-decision.** From
the daily trending summary for Sun 1 Nov 2026 (the latest available
at this 08:52 build; the 09:00 summary for today runs after this job):

- Agent harness engineering was #2 (LangGraph state, threads,
  checkpointers, memory, approval) and AI evals + observability +
  cost-per-decision was #4, with prompt caching newly prominent.
- The social stack had converged on "LLM = brain, LangGraph = nerves,
  MCP = hands" — i.e. the harness around the model is the skill.

A fresh search on the morning of 2 Nov 2026 reinforced the same
point from the other side: an "agent harness tax" piece
(https://autocoder.dev/blog/harness-tax-cost-per-solved-task) argues
the harness — loop, tools, context compaction, cache discipline —
moves cost per solved task far more than swapping the model, and a
Q3 2026 field report
(https://imiel.dev/explore/state-of-ai-agents-q3-2026/) notes price
per task, not price per token, is now the headline metric. This tool
implements that metric for your own logs, with your own prices.

This is deliberately not another ML classifier and not a repeat of
Day 04's MCP server: Day 04 showed how an agent *calls* a tool; this
shows how to *measure* whether the harness around the model is worth
what it costs.

## How to run

No dependencies — Python 3.10+ standard library only.

```bash
python3 analyzer.py sample_runs.jsonl
python3 analyzer.py runs.jsonl --format json
python3 analyzer.py runs.jsonl --input-price 1.0 --cached-price 0.1 --output-price 5.0
```

Input is one JSON object per line, e.g.:

```json
{"task_id": "t1", "harness": "harness-a", "model": "demo-model",
 "input_tokens": 12000, "cached_input_tokens": 9600,
 "output_tokens": 1500, "solved": true, "steps": 10,
 "tool_calls": 4, "duration_s": 40}
```

`cached_input_tokens` is a subset of `input_tokens`. Prices are per
1M tokens; the defaults ($3.00 uncached input / $0.30 cached /
$15.00 output) are illustrative only, NOT any provider's real price
list — pass your model's real prices with the flags above.
Malformed lines are skipped with a warning, not a crash; a harness
with zero solved tasks reports cost/solved as `n/a` (never $0) and
sorts last.

## Example input / output (actually run, 2 Nov 2026)

`sample_runs.jsonl` is **synthetic demo data, clearly labelled as
such** — two made-up harnesses on the same four tasks, with the same
model. It is not a benchmark of any real agent or provider.

```
$ python3 analyzer.py sample_runs.jsonl
harness-a: 3/4 solved (75%), total $0.1280, cost/task $0.0320, cost/solved $0.0427, tokens/solved 17633
    cache hit 80%, avg steps 10.5, avg tool calls 4.5, avg duration 41.2s
harness-b: 2/4 solved (50%), total $0.4000, cost/task $0.1000, cost/solved $0.2000, tokens/solved 39250
    cache hit 20%, avg steps 19.8, avg tool calls 9.5, avg duration 98.8s

Cheapest per solved task: harness-a at $0.0427
```

The demo's lesson is the metric itself: harness-b is only ~3x more
expensive per task, but ~4.7x more expensive per *solved* task
($0.2000 vs $0.0427), because it also solves fewer tasks while
burning more tokens on the failures — low cache hit (20% vs 80%),
more steps, more tool calls. Ranking by cost per token alone would
hide that.

## Tests

```bash
python3 -m unittest test_analyzer -v
```

5 tests, all passing on 2 Nov 2026: cached tokens priced at the
cached rate, cost-per-solved penalising failed tasks, zero-solved
harnesses sorting last with `n/a`, malformed lines skipped, and
cache-hit-rate maths.

## 2-minute interview explainer

**Problem.** Picking an agent by its model's benchmark score optimises
the wrong thing: in production you pay per task attempted, and a
harness that retries, re-reads context, and never caches can cost
several times more per task actually finished — even with the same
model. Teams need one number that combines success and spend.

**Approach.** A stdlib-only CLI that reads JSONL run logs (task,
harness, input/cached/output tokens, solved flag, steps, tool calls,
duration), prices tokens from command-line rates (cached tokens at
the cheaper cached rate, since they are a subset of input), and
aggregates per harness: success rate, total cost, cost per task,
cost per solved task, tokens per solved task, cache hit rate, and
average steps/tool calls/duration. Harnesses sort by cost per solved
task; unsolved-only harnesses report `n/a` rather than a misleading
zero. Malformed log lines are counted and skipped.

**Results.** On the synthetic demo (same model, same four tasks):
harness-a solved 3/4 at $0.0427 per solved task with an 80% cache hit
rate; harness-b solved 2/4 at $0.2000 per solved task with a 20%
cache hit rate. The 5 unit tests pin the pricing and ranking logic,
including the edge cases above.

**Limits — stated honestly.** The demo data is invented to show the
metric, not a measurement of any real harness or model, and the
default prices are illustrative, not a provider price list. The tool
does not judge task quality (a "solved" flag is only as good as the
grader that set it), does not handle streaming/live runs, and does
not account for non-token costs (infra, human review, latency value).
The natural next steps would be a real grader hookup, per-model
price presets, and a time-series view so a harness regression shows
up as a rising cost-per-solved line.
