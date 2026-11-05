# Day 10 — Local RAG Q&A with a Retrieval Eval (Day A: trending-skill build)

A stdlib-only Python RAG pipeline you can run offline: chunk
documents, retrieve with TF-IDF cosine similarity, and answer
**only** from the retrieved passage — with its source and score.
If nothing scores above the threshold, it says "Not found in the
provided documents" instead of inventing an answer.

## The trend this builds with

**RAG + AI evals.** From the daily trending summary for Wed 4 Nov
2026 (the latest available at this 08:52 build; the 09:00 summary
for today runs after this job): RAG was a top skill, alongside
agentic AI, evals + observability, and governance/guardrails.
A fresh search on the morning of 5 Nov 2026 pointed the same way:
an AI Builders Network piece (4 Nov 2026) calls applied LLM
engineering — RAG, agents, prompt/context engineering, and evals —
the default high-ROI path, and calls evals "the unglamorous edge";
a 390-job-posting roadmap analysis (4 Nov 2026) puts evals at 56%
of postings and RAG at 26%.

This is deliberately not a repeat of earlier days: Day 03 matched
a resume against job descriptions, Day 04 gave an agent tools via
MCP, and Day 07 measured agent-run cost. This one builds the
retrieval + eval half of RAG itself — the part that has to work
before any generator is worth judging.

## How to run

No dependencies — Python 3.10+ standard library only.

```bash
python run.py "Why use overlap when chunking long documents?"
python run.py --eval
python -m unittest test_rag -v
```

Example output (actually run, 5 Nov 2026):

```
ANSWER (retrieved passage):
Chunking splits long documents into retrievable pieces. ...
SOURCES:
  chunking chunking#c0 score=0.4099
```

An unrelated question is refused, not answered:

```
$ python run.py "quantum chromodynamics lattice gauge theory"
Not found in the provided documents.
```

## Results (actually run, not hard-coded)

- Tests: **4/4 pass**.
- Retrieval eval on the 8-question golden set in `eval.json`:
  **recall@1 = 1.0, recall@3 = 1.0, MRR@3 = 1.0**.
- Honest caveat: the docs in `docs.json` are small and synthetic,
  clearly labelled as such, and the eval questions reuse the docs'
  own vocabulary — so a perfect score here proves the pipeline
  works end to end, not that it would score 1.0 on a real corpus.
  The eval is the point: swap in real docs and harder, paraphrased
  questions and the same command measures the drop.

## How it works

1. `chunk_text` splits each doc into 40-word windows with
   10-word overlap, so a sentence on a boundary survives.
2. `TfIdfIndex` builds smoothed TF-IDF vectors and ranks chunks
   by cosine similarity to the query.
3. `answer` returns the top passage with sources, or refuses
   below a 0.15 score threshold.
4. `evaluate` reports recall@1, recall@k, and MRR against
   `eval.json`.

## Limits

- TF-IDF matches words, not meaning: a paraphrased question with
  none of the doc's vocabulary will score low and be refused.
  Dense embeddings (the next step) would fix paraphrase, not
  exact-term matching.
- Fixed word windows can cut a sentence mid-way; sentence-aware
  chunking is the next improvement, measured on the same eval.
- There is no LLM generator here, so "answers" are retrieved
  passages, not fluent summaries — by design, so nothing is
  generated beyond what was retrieved.

## 2-minute explainer

**Problem:** RAG demos usually show a chatbot answer with no proof
it came from the documents, and no measurement of whether retrieval
even worked. **Approach:** I built the retrieval half properly and
offline — chunking with overlap, TF-IDF retrieval, a score
threshold that refuses ungrounded questions, and a golden-set eval
reporting recall and MRR. **Results:** 4/4 tests pass and the
retriever gets all 8 synthetic questions right at rank 1, with a
clean refusal on an out-of-corpus question. **Limits:** it is a
word-matching retriever on synthetic docs, so paraphrase is its
weakness and the perfect eval score should not be read as a
real-world score — the eval harness is what transfers to real data.
