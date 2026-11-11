# Day 16 — LangGraph RAG Agent with a Human Approval Gate (Day A: trending-skill build)

A small LangGraph agent that answers questions from a local document set
using a TF-IDF retriever as its tool, pauses for human approval before
answering, and logs every run as a JSONL trace — with a 10-case eval.

## The trend this builds with

**LangGraph / agentic AI + evals + observability.** From the daily trending
summary for Tue 10 Nov 2026, which suggested exactly this as the next Day A
build: a tiny LangGraph agent calling the Day 10 RAG as a tool, with an
approval gate, a 10-case eval and a JSONL trace log. A fresh search on the
morning of 11 Nov 2026 confirms it:

- **Skillenai** (LangGraph jobs page, 90 days ending 5 Nov 2026): LangGraph
  appears in **2,843 job postings**, demand share **up 5.3%** vs the prior
  4 weeks. **43.1% of Agentic AI Engineer** postings mention LangGraph,
  37.5% of GenAI Engineer postings do.
- **getreadyforagents.com** (2,521 open agentic AI roles, 9 Nov 2026):
  LangGraph in **14%** of roles; RAG 27%, MCP 27%.
- **Scaler / CIEL HR**: demand for agentic AI engineers in India rose
  **260% year on year** in 2026; Gartner expects 40% of enterprise apps to
  include task-specific agents by end of 2026.

This is deliberately not a repeat of earlier days: Day 04 gave an agent
tools via MCP, Day 07 measured agent-run cost, Day 10 built the RAG
retrieval + eval half. This one wires retrieval into a real LangGraph
state machine with a human-in-the-loop gate and per-run traces — the
orchestration half.

## The graph

```
START -> retrieve -> route
  route: top score >= 0.15 -> approval_gate
         top score <  0.15 -> refuse
approval_gate -> approved? -> answer
              -> not approved -> refuse
answer / refuse -> END
```

- `retrieve` — calls the TF-IDF retriever (`retrieval.py`) as the agent's
  tool, over 10 short synthetic docs about a fictional makerspace,
  ForgeLab (clearly labelled synthetic in `docs.json`).
- `approval_gate` — a real LangGraph human-in-the-loop step: it calls
  `interrupt()` and pauses until a human resumes. Pass `--auto-approve`
  (used by the eval and tests) to skip the pause.
- `answer` — a local deterministic stand-in for an LLM call: it composes
  the answer from the top retrieved passage and cites it. **No model API,
  no paid calls, no API key needed.** Swapping in a real chat model means
  replacing this one node — the graph, tool, gate and traces stay the same.
- Every node appends to the run trace; `run.py` writes one JSONL line per
  run to `traces.jsonl` (question, nodes visited, top score, decision,
  latency) — the observability half.

## How to run

```bash
pip install -r requirements.txt   # langgraph==1.2.20
python run.py "Which 3D printers does ForgeLab have?" --auto-approve
python run.py "What safety gear is required in the workshop zone?"
python run.py --eval              # 10-case golden-set eval
python -m unittest test_agent -v  # 7 tests
```

Without `--auto-approve` the graph pauses at the gate and asks on the
terminal; answer `y` to approve, `n` to refuse.

## Example output (actually run, 11 Nov 2026)

```bash
$ python run.py "Which 3D printers does ForgeLab have?" --auto-approve

ForgeLab has two Prusa MK4 3D printers. Book a printer on the ForgeLab
booking board. Each booking is limited to a maximum of 4 hours, and
filament is charged by weight. [source: 3D printers, retrieval score=0.421]

[decision=answered nodes=retrieve -> approval_gate:auto-approved -> answer
 top_score=0.4208 latency=9.9ms]
```

An out-of-scope question is refused, not answered:

```bash
$ python run.py "What is the capital of France?" --auto-approve

Not found in the provided documents.

[decision=refused nodes=retrieve -> refuse top_score=0.0 latency=9.6ms]
```

The interactive gate, approved and declined (actually run):

```bash
$ python run.py "What safety gear is required in the workshop zone?"
HUMAN GATE — the agent wants approval before answering:
  Question: What safety gear is required in the workshop zone?
  Draft (from Safety rules (score=0.334)): Eye protection is mandatory ...
Approve this answer? [y/n] y
Eye protection is mandatory in the workshop zone at all times. ...
[decision=answered nodes=retrieve -> approval_gate:human-decision -> answer ...]

# answering n instead:
Not approved at the human gate.
[decision=refused nodes=retrieve -> approval_gate:human-decision -> refuse ...]
```

## Results (actually run, not hard-coded)

- Tests: **7/7 pass** (retriever, graph end-to-end, gate pause + approve,
  gate decline, eval metrics).
- Eval on the 10-case golden set in `eval.json` (8 answerable + 2
  out-of-scope): **recall@1 = 1.0, recall@3 = 1.0, answer accuracy = 1.0,
  refusal accuracy = 1.0**. Full per-case results in `eval_results.json`.
- Two bugs found and fixed while testing, both with failing tests first:
  stopwords (`what/is/the/of`) inflated out-of-scope scores to 0.24, so
  retrieval now drops them; the trace list used the wrong reducer, so only
  the last node was recorded — now `operator.add`, and traces show the full
  `retrieve -> approval_gate -> answer` path.

## 2-minute interview explainer

**Problem:** an agent that answers from documents needs three things
before it is trustworthy: retrieval that actually finds the right passage,
a human check before it speaks, and a record of what it did so failures
can be debugged. **Approach:** a LangGraph `StateGraph` with four nodes —
`retrieve` (TF-IDF over a small local corpus, top-3 with cosine scores),
a conditional route on a 0.15 score threshold, an `approval_gate` node
that uses LangGraph's `interrupt()` to pause for a human decision, and an
`answer` node that cites its source. A `MemorySaver` checkpointer holds
the paused state so the run can resume. Every run appends a JSONL trace
line, and a 10-case golden set measures recall, answer accuracy and
refusal accuracy. **Results:** 7/7 tests pass; eval is 1.0 on all four
metrics on the small synthetic set. **Limits:** the docs are 10 short
synthetic passages, so the 1.0 scores show the pipeline works, not that
it generalises; the answer node is a deterministic stand-in, not an LLM,
so there is no generation, no paraphrasing and no handling of questions
that need synthesis across passages; the 0.15 threshold was set by
inspection on this corpus, not tuned.

## Files

- `agent.py` — the LangGraph state machine (graph, nodes, gate, resume)
- `retrieval.py` — stdlib TF-IDF retriever (the agent's RAG tool)
- `run.py` — CLI, interactive gate, eval runner, JSONL trace writer
- `docs.json` — 10 short synthetic ForgeLab docs (labelled synthetic)
- `eval.json` — 10-case golden set (8 answerable, 2 out-of-scope)
- `test_agent.py` — 7 unittest tests
- `eval_results.json` — eval output (generated by `--eval`)
- `traces.jsonl` — one JSONL line per run (generated)
- `requirements.txt` — `langgraph==1.2.20`
