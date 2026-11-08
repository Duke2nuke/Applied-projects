# Day 13 — Context Budget Packer (Day A: trending-skill)

A small stdlib-only Python tool for **context engineering**: fitting
exactly what a model should see — system instructions, few-shot
examples, retrieved documents, tool results and conversation history —
into a fixed token budget, and proving what was kept, trimmed,
compacted or dropped before any model call is made.

## The trend, and the sources

Context engineering is the named skill replacing prompt engineering
in late 2026: the job is no longer wording one prompt well, but
deciding what the model sees on each call — memory, compaction,
sub-agents and tool design, with RAG as one technique inside it
(daily trending summary, 7 Nov 2026). The same week's hiring data
backs it up: evals appear in 56% of AI Engineer job descriptions
and agents in 50% (Dexity, 390 JDs, Jul 2026; Agent Native, 1,376
roles, Oct 2026), LangGraph is the production agent default after
its 1.0 release, and MCP passed 110M monthly SDK downloads and now
sits under the Linux Foundation — the agent stack is now
infrastructure, and context is the part of it a builder controls
directly. Fresh check this morning (8 Nov 2026): the same signals
hold — context engineering, LangGraph/MCP, evals and observability
lead every 2026 AI-engineer roadmap
([KodeKloud](https://kodekloud.com/blog/ai-engineer-roadmap/),
[yashpokar.com](https://www.yashpokar.com/blog/what-the-ai-engineering-market-actually-wants-in-2026)).

This project practices the skill itself: no model API, no downloads,
no API key — the packing logic is the whole point, and it runs
offline on synthetic demo data.

## How to run

No dependencies — Python 3.10+ standard library only.

```bash
python3 context_packer.py example/context.json --budget 600   # pack the demo
python3 context_packer.py example/context.json --budget 400   # tight budget
python3 context_packer.py example/context.json --budget 400 --policy drop      # drop-only
python3 context_packer.py example/context.json --budget 400 --policy truncate  # trim-only
python3 test_context_packer.py                                 # automated checks
```

Options: `--budget N` (overrides the budget in the JSON file),
`--policy compact|truncate|drop` (default `compact`),
`--prompt-only` (print just the packed prompt, no report).

The JSON file is `{"budget": N, "items": [...]}`; each item has a
`kind` (system, examples, retrieved, tool_result, history), `text`,
`priority` (0–100, higher kept first), `must_include` (always kept)
and a `label` for reports. All example text is synthetic demo data.

## Example input / output (actually run, 8 Nov 2026)

Input — `example/context.json`: a coding-assistant call with 8
items (synthetic): system instructions (must-include), two few-shot
examples, three retrieved doc chunks, two tool results, six turns
of chat history. Total requested: **716 tokens (estimate)**.

At `--budget 600` with the default `compact` policy, everything
fits — the history is compacted instead of dropped:

```
Budget: 600 tokens (estimate) | requested: 716 | used: 590 (98% of budget)
Kept 8, dropped 0.
  [keep] system: coding assistant instructions (system, prio 100): 80 -> 80 tokens
  [keep] examples: two few-shot Q&A pairs (examples, prio 80): 76 -> 76 tokens
  [keep] retrieved: pathlib docs chunk (retrieved, prio 70): 86 -> 86 tokens
  [keep] tool: pytest output (tool_result, prio 65): 79 -> 79 tokens
  [keep] retrieved: argparse docs chunk (retrieved, prio 60): 81 -> 81 tokens
  [keep] tool: file listing (tool_result, prio 55): 70 -> 70 tokens
  [keep] retrieved: testing notes chunk (retrieved, prio 50): 81 -> 81 tokens
  [pack] history: 6 earlier turns (history, prio 40): 163 -> 37 tokens — history compacted 163 -> 37 tokens
```

The compacted history keeps the first sentence of the oldest turn
plus the full latest turn:

```
[HISTORY] [earlier] User: I want a tool that packs LLM context into a token budget.
Assistant: Running it now with an 800-token budget and the compact policy.
```

At `--budget 400` the same input forces real trade-offs — the
lowest-priority items go first, and the budget is never exceeded:

```
Budget: 400 tokens (estimate) | requested: 716 | used: 400 (100% of budget)
Kept 5, dropped 3.
  [keep] system: coding assistant instructions (system, prio 100): 80 -> 80 tokens
  [keep] examples: two few-shot Q&A pairs (examples, prio 80): 76 -> 76 tokens
  [keep] retrieved: pathlib docs chunk (retrieved, prio 70): 86 -> 86 tokens
  [keep] tool: pytest output (tool_result, prio 65): 79 -> 79 tokens
  [trim] retrieved: argparse docs chunk (retrieved, prio 60): 81 -> 79 tokens — cut to fit remaining 79 tokens
  [drop] tool: file listing (tool_result, prio 55): 70 -> 0 tokens — needs 70 tokens, 0 left
  [drop] retrieved: testing notes chunk (retrieved, prio 50): 81 -> 0 tokens — needs 81 tokens, 0 left
  [drop] history: 6 earlier turns (history, prio 40): 163 -> 0 tokens — needs 163 tokens, 0 left
```

With `--policy drop` at the same budget, the argparse chunk is
dropped whole instead of trimmed and the file listing survives —
same budget, different trade-off, visible in the report.

## How it works

1. **Estimate.** Token counts are a chars/4 heuristic, labelled an
   estimate everywhere. Real tokenisers differ per model; the
   estimate is good enough to compare policies and stay under a
   budget, and it is one function to swap for a real tokenizer.
2. **Order by priority, assemble by kind.** Optional items fill the
   budget highest-priority first (ties: fewer tokens, then kind
   order, so runs are deterministic). The final prompt is then
   re-ordered by kind — system, examples, retrieved, tool results,
   history — so the model reads a coherent prompt, not a priority
   ranking.
3. **Overflow policies.** `compact` compacts history first
   (extractive summary: first sentence of each older turn + the
   full latest turn), then truncates long items to the remaining
   budget, then drops lowest priority. `truncate` skips the
   compaction step; `drop` drops whole items only. Must-include
   items are always kept and are only truncated if they alone
   exceed the budget.
4. **Report everything.** Every item gets a decision line — kept,
   trimmed, compacted or dropped, with requested vs used tokens
   and the reason — so a dropped document is a visible choice,
   not a silent loss.

## 2-minute interview explainer

**Problem:** an agent call has a fixed context window, but the
context it wants — instructions, examples, retrieved docs, tool
outputs, chat history — almost never fits. Builders either truncate
blindly and lose the wrong thing, or pay for a bigger window and
still waste tokens on stale history. The skill the market now names
for this is context engineering, and it is mostly judgement calls
made invisible.

**Approach:** a stdlib-only packer that takes labelled context items
with a kind, a priority and a must-include flag, and fits them into
a token budget under one of three explicit policies — compact,
truncate, or drop. History compacts extractively (first sentence of
each older turn, full latest turn), items fill in priority order,
the prompt is re-assembled in kind order, and every decision is
reported with requested vs used tokens and a reason.

**Results:** on the bundled demo (716 tokens requested), a 600-token
budget keeps all 8 items by compacting history 163 → 37 tokens
(98% utilisation, 0 dropped); a 400-token budget keeps the 5
highest-priority items, trims one, and drops 3, at exactly 100% of
budget. 11 automated tests pass, covering the budget cap,
must-include behaviour, drop order, truncation, compaction, empty
input and determinism.

**Limits:** token counts are a chars/4 estimate, not a real
tokenizer — for a production call, swap in the model's tokenizer.
Compaction is extractive (first sentences), not a model summary, so
it preserves wording but not nuance. Priorities are set by the
caller; the tool enforces a budget, it does not judge relevance —
a relevance scorer over retrieved chunks is the natural next step.
