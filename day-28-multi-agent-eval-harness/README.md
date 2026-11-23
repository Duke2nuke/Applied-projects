# Day 28 — Multi-Agent Eval Harness with Tracing (Day A: trending-skill)

A stdlib-only Python harness that **runs three agent strategies over a
12-case golden set, grades them deterministically, and writes
OpenTelemetry-style traces** — the "evals + observability" half of
modern AI engineering, with no API key, no downloads and no GPU.

## The trend this builds with

**Evals and observability for multi-agent systems.** Three sources
from the morning of 23 Nov 2026 agree this is the skill to have now:

- "AI Engineer Skills: 15 Required in 2026" (ayautomate.com, updated
  6 days ago): multi-agent orchestration and "evaluation &
  observability" are both on the 15-skill list — "if you cannot
  measure your agent, you cannot ship it", with a versioned eval set,
  a numerical score and a regression alarm as the ship gate.
- "AI Engineering in 2026: Agents, MCP, Evals & Production AI
  Systems" (rajtechbd.com): "Evals: the new unit tests" — golden
  datasets, automated graders, regression gates in CI, online eval.
- "Daily Systems Trends Report — November 13, 2026"
  (blog.punkslack.com): verification is the new bottleneck (best
  frontier coding agent solves only 18.5% of long-horizon multi-step
  chains), OpenTelemetry is the default observability pipe, and
  verification-driven frameworks make *checking*, not generation, the
  coordination signal.

The 21 Nov daily trending scan said the same thing from the jobs
side: evals and observability appear in 87% of agent postings, and
multi-agent evaluation is now a platform feature (Microsoft Ignite).
This project builds the smallest honest version of that: a harness,
not a leaderboard claim.

## What it does

Three agents answer the same 12 questions from the same small fact
store. The "model" is a deterministic keyword retriever over 18
hand-written facts — a stand-in, not a real LLM — so the interesting
part, the machinery around the model, can be run and tested for free:

| Agent | Strategy |
|---|---|
| `direct` | One naive retrieval (raw token overlap), answer from the top fact. The baseline. |
| `planner` | Plan-then-answer: splits two-part questions, retrieves per part with content-word scoring (stopwords and superlatives dropped), carries the previous part's answer forward as context so "its largest moon" resolves "its". |
| `debate` | Propose-then-critique: `direct` drafts, a critic re-checks every part with content-word retrieval and replaces any part resting on the wrong fact. |

Graders are deterministic, no LLM judge: **correctness** (fraction
of gold keywords in the answer), **grounded** (every cited fact must
be in the gold supporting set), **concise** (at most 40 words). The
harness also emits one trace span per step (`agent.run`,
`retrieve`, `plan.retrieve`, `critic.verify`) with duration and
estimated tokens, written to `traces.jsonl`, and a **regression
gate**: it exits non-zero if any agent's mean correctness falls below
`--fail-under` (default 0.7) — the CI ship-gate idea from the trend
pieces above.

## How to run

No dependencies — Python 3.10+ standard library only.

```bash
python3 harness.py
python3 harness.py --agents planner,debate
python3 harness.py --format json
python3 harness.py --fail-under 0.6 --out results.json --traces traces.jsonl
python3 -m unittest -v
```

## Example output (actually run, 23 Nov 2026)

```text
$ python3 harness.py
Golden set: 12 cases (4 simple, 4 two-part, 4 distractor)
agent      correct  grounded  concise  ms/task  tokens*
-------------------------------------------------------
direct       0.625     0.750    1.000     0.19      351
planner      1.000     1.000    1.000     0.43      383
debate       1.000     1.000    1.000     0.58      734
* tokens are estimates (words x 1.3), not a real tokenizer count.
  direct: distractor=0.25, simple=1.00, two-part=0.62
  planner: distractor=1.00, simple=1.00, two-part=1.00
  debate: distractor=1.00, simple=1.00, two-part=1.00
GATE FAILED: direct below 0.7
```

17/17 tests pass (`python3 -m unittest -v`).

## Results — what the eval actually shows

- **Naive retrieval is the failure mode.** `direct` scores 1.00 on
  simple questions but 0.25 on the four distractor questions: "largest
  planet" retrieves the Pacific Ocean fact, "hottest planet" retrieves
  the Sahara, "largest moon in the Solar System" retrieves Earth's
  Moon — each distractor shares the question's words while answering a
  different question. It gets the fourth distractor right only
  because the question names both candidates.
- **Planning fixes it cheaply.** `planner` scores 1.00 everywhere for
  383 estimated tokens vs `direct`'s 351 — a +0.375 correctness gain
  for +9% tokens. Dropping superlatives ("largest", "hottest") from
  retrieval scoring and splitting two-part questions does the work.
- **Debate costs double for zero gain here.** `debate` also scores
  1.00 but uses 734 estimated tokens (1.9x the planner) and the most
  spans per task. The critic only pays when the proposer is wrong in
  ways re-ranking cannot fix — on this set it never is. That is itself
  the eval finding: more agents is not automatically better, measure
  the cost per point.
- **The gate works.** The default run exits 1 because `direct` (0.625)
  is below the 0.7 bar — exactly what a CI regression gate should do
  when a strategy regresses. Run `--agents planner,debate` or
  `--fail-under 0.6` to get a passing exit code.

## 2-minute explainer

**Problem:** AI agents are probabilistic, so "it worked on my laptop"
proves nothing — teams need a repeatable way to compare agent
designs and catch regressions before shipping. **Approach:** I built a
small harness with a 12-case golden set (simple, two-part, and
lexical-distractor questions), three agent strategies over the same
stub model (direct retrieval, plan-then-answer, propose-then-critique),
deterministic graders for correctness, groundedness and conciseness,
plus per-step trace spans and a regression gate that fails the run
below a score bar. **Results:** on the golden set the planner beats
the naive baseline 1.00 vs 0.625 correctness for +9% tokens, while the
debate agent matches the planner at 1.9x the token cost — so the
critic is not worth it here. **Limits:** the model is a keyword
retriever over 18 hand-written facts, not an LLM; the golden set is 12
synthetic cases, so this proves the harness works, not that planner
beats debate in general; token counts are word-count estimates, and
the sub-millisecond latencies are meaningless with a stub model — with
a real LLM the token ratio is the number that matters.

## Limits, stated honestly

- The "model" is a keyword retriever, not an LLM. Any agent can be
  pointed at a real model by implementing the same `retrieve` /
  `answer` interface in `model.py`; nothing here calls a paid API.
- 12 synthetic cases, hand-written facts. Scores describe this set
  only. The harness is the deliverable; the scores are a demo.
- Token counts are estimates (words x 1.3), latencies are real but
  trivially small against a local stub.
- The `direct` agent's failures are engineered into the golden set on
  purpose (distractor facts that share the question's words) — that is
  what a golden set is for: known failure modes, checked on every run.

## Files

- `harness.py` — CLI runner, comparison table, JSON results, traces, gate
- `agents.py` — direct / planner / debate strategies + span tracer
- `model.py` — stub model, fact store, naive vs content-word retrieval
- `graders.py` — correctness / grounded / concise graders
- `golden.json` — the 12-case golden set (questions, keywords, supporting facts)
- `facts.json` — the 18-fact store (synthetic demo data, distractors listed first)
- `test_harness.py` — 17 tests (graders, retrieval, agents, traces, gate)
- `results.json`, `traces.jsonl` — output of the latest run
