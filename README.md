# Applied Projects

Applied, working projects — mixed across languages and topics,
trending where it makes sense, with a slight lean towards ML + Python.

Each project is a folder with its own README, runnable code, and a
2-minute explainer, so every project can actually be talked about
in an interview — not just listed.

## Plan

- ML / Python (a bit more often): classifiers, NLP, vision, data
- Mixed: JavaScript/TypeScript tools, web apps, automation, Flutter,
  Go/Rust tools, LLM apps, trending topics
- Rule: no project goes on a resume until its explainer is understood

## Projects

- Day 01 — Prompt Injection Detector (ML, Python): TF-IDF + Logistic
  Regression classifier for benign vs injection prompts.
  See `day-01-prompt-injection-detector/`.
- Day 02 — Server Metrics Anomaly Detector (ML, Python):
  unsupervised, same-hour seasonal baseline + median/MAD modified
  z-score detector for CPU, memory, latency, and request-rate
  anomalies in synthetic server metrics.
  See `day-02-server-anomaly-detector/`.
- Day 03 — Resume–Job Description Matcher (ML, Python): TF-IDF
  cosine-similarity ranking of job postings against a resume, with
  a matched-vs-missing skill-gap report per posting. Stdlib only,
  synthetic demo data.
  See `day-03-resume-jd-matcher/`.
- Day 04 — Mini MCP Notes Server (Day A: trending-skill, Python):
  stdlib-only Model Context Protocol server over stdio JSON-RPC,
  exposing add_note / list_notes / search_notes tools with JSON
  persistence and an automated subprocess test harness.
  See `day-04-mcp-notes-server/`.
- Day 05 — Customer Segmentation with K-Means, from Scratch
  (Day B: AI/ML Python): stdlib-only K-means++ clustering of
  synthetic customers (age, income, spending score), with elbow
  table, silhouette score, and cluster profiles. Silhouette 0.475
  at k=4; clusters recover the planted segments.
  See `day-05-customer-segmentation/`.
- Day 06 — Markdown Link Checker (Day C: community / open-source):
  stdlib-only CLI that finds broken local-file links and missing
  heading anchors in Markdown docs, with optional remote checking
  and JSON output. MIT-licensed, with example docs and 5 passing
  tests. See `day-06-markdown-link-checker/`.
- Day 07 — Agent-Run Cost & Eval Analyser (Day A: trending-skill):
  stdlib-only CLI that turns JSONL agent run logs into cost per
  solved task, success rate, cache hit rate, and tokens per solved
  task per harness, ranked cheapest-per-solved first. Synthetic demo:
  harness-a $0.0427/solved (75%, 80% cache) vs harness-b
  $0.2000/solved (50%, 20% cache). 5 passing tests.
  See `day-07-agent-cost-eval-analyzer/`.
- Day 08 — House Price Predictor with Linear Regression, from Scratch
  (Day B: AI/ML Python): stdlib-only regression on synthetic housing
  data, with standardisation, gradient descent checked against the
  exact closed-form solution, and a held-out test report. Test
  R^2=0.980, MAE=$12,279; recovered $150/sq ft matches the true
  generating weight. 5 passing tests.
  See `day-08-house-price-regression/`.
- Day 10 — Local RAG Q&A with a Retrieval Eval (Day A: trending-skill):
  stdlib-only Python RAG — chunking with overlap, TF-IDF retrieval,
  grounded answers with sources, refusal below a score threshold,
  and a golden-set eval. 4/4 tests pass; recall@1 = 1.0 on the
  8-question synthetic set (questions reuse doc vocabulary, so this
  proves the pipeline, not a real-corpus score).
  See `day-10-local-rag-qa/`.
- Day 09 — Duplicate File Finder (Day C: community / open-source):
  stdlib-only CLI that finds byte-identical files by size grouping
  then SHA-256 hashing, reports recoverable space, and never deletes
  anything (report-only by design), with JSON output, excludes, and
  a minimum-size filter. MIT-licensed, with example docs and 6
  passing tests. See `day-09-duplicate-file-finder/`.
- Day 11 — Daily Demand Forecaster (Day B: AI/ML Python):
  stdlib-only time-series forecasting on 365 synthetic days of
  canteen orders — ridge regression on lags 1/7/14, trend and
  day-of-week, vs naive and seasonal-naive baselines, evaluated
  walk-forward. MAE 7.60 vs seasonal-naive 9.07; 7/7 tests pass.
  See `day-11-daily-demand-forecaster/`.
- Day 12 — TODO Sweeper (Day C: community / open-source):
  stdlib-only CLI that sweeps a directory tree for TODO, FIXME,
  HACK, XXX, NOTE and BUG marker comments, comment-aware so
  "TODOLIST", prose "bug" and string literals are not flagged,
  grouped by tag with file:line, JSON output and a Markdown
  report, linter-style exit codes. MIT-licensed, with example
  docs and 7 passing tests. See `day-12-todo-sweeper/`.
- Day 13 — Context Budget Packer (Day A: trending-skill):
  stdlib-only context-engineering tool that fits system
  instructions, examples, retrieved docs, tool results and chat
  history into a token budget under compact/truncate/drop
  policies, with history compaction and a per-item budget report.
  Demo (716 tokens requested): 600-token budget keeps all 8
  items, history compacted 163 -> 37 tokens; 400-token budget
  keeps 5, trims 1, drops 3. 11 passing tests.
  See `day-13-context-budget-packer/`.
- Day 14 — Movie Recommender (Day B: AI/ML Python):
  stdlib-only item-based collaborative filtering on 1,163 synthetic
  ratings (60 users, 40 movies) — adjusted cosine similarity on
  mean-centred ratings, shrunk by co-rater count, top-10 neighbour
  prediction, popularity fallback for cold-start users. Held-out
  RMSE 0.648 vs global-mean 0.710 and user-mean 0.738; Precision@5
  0.153, Recall@5 0.506. 7 passing tests.
  See `day-14-movie-recommender/`.
- Day 15 — LogLens (Day C: community / open-source): stdlib-only CLI
  that summarises web access logs and plain-text app logs — status
  breakdown and error rate, top paths/IPs, paths with most errors,
  slowest requests, and the actual error lines, with JSON output.
  On the 12-line synthetic access log: 58.3% error rate, worst path
  `/old-page` (3× 404), slowest request 1.284 s returning a 500.
  MIT-licensed, with example logs and 11 passing tests.
  See `day-15-log-analyzer/`.
