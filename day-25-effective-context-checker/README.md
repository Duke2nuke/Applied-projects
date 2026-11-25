# Day 25 — Effective-Context Checker (Day A: trending-skill)

A stdlib-only CLI that answers the question behind the current
context-engineering trend: **is your prompt inside the part of the
context window the model can actually use?**

## The trend

- **Effective context, not context window** — Threads @dearsum1, 18 Nov
  2026 (flagged in the 19 Nov daily trending-skills summary): a 1M-token
  window does not mean 1M tokens of equal reasoning. Blindly stuffing
  context raises cost and latency without accuracy; the practitioner gap
  is knowing the *effective* context per model and validating with evals.
- Reinforced 20 Nov by fresh search: WisdomAI's "AI Context Engineer"
  2026 career guide (73% of companies already have someone owning AI
  context) and Anthropic's "Effective context engineering" (29 Sep 2025).
  Context engineering — what to keep, retrieve, compress, and validate
  with evals — is the named skill replacing prompt engineering.
- Builds on Day 13 (Context Budget Packer): Day 13 packs context to a
  budget; this one checks a prompt against a model's *effective*
  limit and proves, with a runnable eval, that retrieval degrades as
  context grows.

## What it does

- `check` — estimates tokens for a prompt file (chars/4 heuristic),
  compares it with a model's **advertised** and **effective** context,
  and returns a verdict: `OK` / `WARNING` (past effective, still inside
  advertised) / `OVER` (past advertised). Also estimates input cost per
  call and per 100 calls.
- `eval` — a tiny needle-retrieval eval: plants one fact ("The current
  vault passcode is 84712") mid-context among distractors that share the
  query words with a different, retired code, then retrieves with a
  TF-IDF-ish keyword scorer over ~150-word chunks at growing context
  sizes. Shows hit rate decaying as context grows.
- `models` — lists the built-in model table (advertised window,
  effective-context working estimate, approx. input price per 1M tokens).

## How to run

No dependencies — Python 3.10+ standard library only.

```bash
python3 context_check.py check --model gpt-4o-mini --file examples/sample-prompt.txt
python3 context_check.py check --model gpt-4o-mini --file examples/sample-prompt.txt --effective-tokens 4000
python3 context_check.py eval
python3 context_check.py models
python3 -m unittest test_context_check -v
```

## Example output (actually run)

`check` on the bundled synthetic ticket dump (60 tickets, 3,274 words):

```
Model: gpt-4o-mini
Prompt: 19260 chars, 3274 words
Tokens (est.): ~4815 (chars/4: 4815, words*1.33: 4354)
Advertised window: 128,000 tokens -> 3.8% used
Effective context: 64,000 tokens (50% of advertised) -> 7.5% used
Verdict: OK
Est. input cost: $0.0007/call ($0.07 per 100 calls) at $0.15/1M input tokens (approx.)
```

Same prompt with a forced `--effective-tokens 4000` (to show the warning
path): verdict `WARNING`, 120.4% of effective context, exit code still 0.
A prompt past the advertised window returns `OVER` with exit code 1.

`eval` (5 trials per size, seed 42 — full numbers in `eval_results.json`):

```
target_tokens  trials  hit@1  hit@3
-----------------------------------
500            5       1.0    1.0
1000           5       0.4    1.0
2000           5       0.0    0.8
4000           5       0.0    0.0
8000           5       0.0    0.0
```

Top-1 retrieval is perfect at 500 tokens and zero by 2,000; even top-3
is zero by 4,000. That is the whole point of effective context: the
needle is still in the text, the retriever just cannot find it any more.

## Tests

15/15 unittest pass (`python3 -m unittest test_context_check`):
token-estimate sanity, verdict thresholds incl. the effective-context
boundary, cost maths, model-table sanity, eval determinism (same seed,
same rows), needle in exactly one chunk, and CLI end-to-end (check OK,
unknown model exits 2, `models` lists).

## 2-minute explainer

**Problem:** models advertise 128k–1M token windows, but published
long-context evals show retrieval and reasoning degrading well before
the limit, so teams pay for context the model cannot really use.

**Approach:** a stdlib-only checker that (1) estimates prompt tokens
with the standard chars/4 heuristic, (2) compares them against both the
advertised window and a conservative effective-context estimate per
model (about half the advertised window, less for 1M-token windows),
and (3) ships a runnable needle-retrieval eval that measures the decay
directly instead of asserting it.

**Results:** on the bundled 60-ticket synthetic prompt (~4,815 tokens)
every listed model is comfortably OK; the eval shows top-1 hit rate
falling 1.0 → 0.4 → 0.0 as context grows 500 → 1,000 → 2,000 tokens,
and top-3 hitting 0.0 by 4,000 tokens. All 15 tests pass.

**Limits:** token counts are a heuristic, not a real tokenizer — good
enough for fit/borderline/too-big decisions, not exact billing.
Effective-context figures are conservative working estimates from
public long-context evals, not vendor claims and not measured
benchmarks for these exact models; override them with
`--effective-tokens` when you have a better number. Prices are
approximate public list prices (Nov 2026, input tokens only). The eval
uses a keyword retriever on synthetic text, so it demonstrates the
direction of the effect, not a production RAG score.

## Files

- `context_check.py` — the CLI (`check` / `eval` / `models`)
- `models.json` — model table with the working-estimate caveat
- `test_context_check.py` — 15 tests
- `eval_results.json` — the eval numbers above, as run
- `examples/sample-prompt.txt` — synthetic 60-ticket dump (labelled synthetic)
- `requirements.txt` — stdlib only
