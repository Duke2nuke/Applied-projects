"""Effective-context checker: is your prompt inside the part of the
context window the model can actually use?

Advertised context windows (128k, 200k, 1M tokens) are not the same as
*effective* context: published long-context evals (RULER, needle-in-a-
haystack) consistently show reasoning and retrieval degrading well
before the advertised limit. This tool, stdlib only:

  check  -- estimate tokens, cost and a verdict for a prompt file
           against a model's advertised AND effective context.
  eval   -- run a tiny needle-retrieval eval at growing context sizes
           and show hit rate decaying as context grows.
  models -- list the built-in model table.

Effective-context numbers in models.json are conservative working
estimates (roughly half the advertised window, less for 1M-token
windows), NOT vendor claims and NOT measured benchmarks. Override
them with --effective-tokens / --price-per-1m whenever you have a
better number. Token counts are a chars/4 heuristic, not a real
tokenizer: good enough to decide "fits / borderline / too big",
not exact billing.
"""

import argparse
import json
import math
import random
import re
import sys
from pathlib import Path

MODELS_PATH = Path(__file__).with_name("models.json")

WORD_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "the", "a", "an", "is", "was", "are", "were", "of", "to", "in", "on",
    "and", "or", "for", "with", "by", "at", "it", "this", "that", "what",
    "how", "when", "where", "who", "which", "be", "been", "has", "have",
    "had", "do", "does", "did", "as", "from", "into", "over", "under",
}

# ---------------------------------------------------------------- models

def load_models(path=MODELS_PATH):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return {m["name"]: m for m in data["models"]}


def estimate_tokens(text):
    """Heuristic token estimate. Returns (estimate, chars/4, words*1.33)."""
    chars = len(text)
    words = len(text.split())
    by_chars = chars / 4.0
    by_words = words * 1.33
    return max(by_chars, by_words), by_chars, by_words


def verdict(tokens, advertised, effective):
    if tokens > advertised:
        return "OVER"
    if tokens > effective:
        return "WARNING"
    return "OK"


def check_prompt(text, model, effective_override=None, price_override=None):
    tokens, by_chars, by_words = estimate_tokens(text)
    advertised = model["advertised_tokens"]
    effective = effective_override or model["effective_tokens"]
    price = price_override if price_override is not None else model["input_price_per_1m_usd"]
    cost = tokens / 1_000_000 * price
    return {
        "model": model["name"],
        "chars": len(text),
        "words": len(text.split()),
        "tokens_chars_div_4": round(by_chars),
        "tokens_words_x_1.33": round(by_words),
        "tokens_estimate": round(tokens),
        "advertised_tokens": advertised,
        "effective_tokens": effective,
        "effective_pct_of_advertised": round(100 * effective / advertised),
        "pct_of_advertised": round(100 * tokens / advertised, 1),
        "pct_of_effective": round(100 * tokens / effective, 1),
        "verdict": verdict(tokens, advertised, effective),
        "input_price_per_1m_usd": price,
        "cost_per_call_usd": round(cost, 4),
        "cost_per_100_calls_usd": round(cost * 100, 2),
    }


def format_check(result):
    v = result["verdict"]
    flag = {"OK": "OK", "WARNING": "WARNING", "OVER": "OVER"}[v]
    lines = [
        f"Model: {result['model']}",
        f"Prompt: {result['chars']} chars, {result['words']} words",
        f"Tokens (est.): ~{result['tokens_estimate']} "
        f"(chars/4: {result['tokens_chars_div_4']}, words*1.33: {result['tokens_words_x_1.33']})",
        f"Advertised window: {result['advertised_tokens']:,} tokens "
        f"-> {result['pct_of_advertised']}% used",
        f"Effective context: {result['effective_tokens']:,} tokens "
        f"({result['effective_pct_of_advertised']}% of advertised) "
        f"-> {result['pct_of_effective']}% used",
        f"Verdict: {flag}",
    ]
    if v == "WARNING":
        lines.append("  Past effective context: expect weaker recall/reasoning; "
                     "trim, retrieve, or summarise before sending.")
    elif v == "OVER":
        lines.append("  Exceeds the advertised window: the model cannot see all "
                     "of this prompt. Must trim or chunk.")
    lines.append(
        f"Est. input cost: ${result['cost_per_call_usd']:.4f}/call "
        f"(${result['cost_per_100_calls_usd']:.2f} per 100 calls) "
        f"at ${result['input_price_per_1m_usd']}/1M input tokens (approx.)"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------- eval

FILLER = [
    "The ForgeLab onboarding guide covers laptop setup, VPN access, and the weekly demo schedule.",
    "Quarterly planning starts on Monday, and every team brings two roadmap items to the review.",
    "The data pipeline retries failed batches three times before paging the on-call engineer.",
    "New hires pair with a mentor for the first two weeks and ship a small fix by day five.",
    "The staging environment resets every night, so test accounts never survive until morning.",
    "Design reviews happen on Thursdays, and the notes live in the shared team drive.",
    "The support rota rotates weekly, and handover notes are due every Friday afternoon.",
    "Our release checklist includes a changelog entry, a rollback plan, and a smoke test.",
    "The office wifi password changes monthly and is posted on the pantry notice board.",
    "Expense reports need receipts for anything over twenty dollars, submitted by month end.",
    "The hiring loop has four stages, and feedback is due within one business day.",
    "Code review turnaround is under four hours during working days, longer over weekends.",
    "The incident playbook starts with declaring severity, then paging the right rotation.",
    "Sprint demos are recorded, and the links are shared in the team channel afterwards.",
    "The analytics dashboard refreshes hourly, except for the billing table, which is daily.",
    "Vendor contracts renew in March, and procurement needs six weeks of lead time.",
    "The security training module takes forty minutes and must be finished before access is granted.",
    "Our backup job runs at 2am, and restores are tested on the first Tuesday each month.",
    "The customer feedback survey goes out after every resolved ticket, rated one to five.",
    "Team lunch is on the last Friday of the month, and dietary needs are collected in advance.",
]

DISTRACTORS = [
    "The current vault passcode was rotated last week; the old one was 31904 and no longer works.",
    "The current vault passcode expired yesterday; the retired code 55271 should be ignored now.",
    "An earlier vault passcode, 90813, was shared in the old runbook and must not be used.",
    "The vault passcode from the previous quarter, 67420, was revoked during the audit.",
    "Someone wrote the old vault passcode 24680 on a sticky note; it was removed and disabled.",
]

NEEDLE = "The current vault passcode is 84712."
QUERY = "What is the current vault passcode?"


def _tokens_of(text):
    return estimate_tokens(text)[0]


def _chunk_words(words, size=150):
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size)]


def _score_chunk(chunk, query_terms, idf):
    counts = {}
    for w in WORD_RE.findall(chunk.lower()):
        counts[w] = counts.get(w, 0) + 1
    return sum(counts.get(t, 0) * idf.get(t, 1.0) for t in query_terms)


def build_context(target_tokens, seed, needle_depth=0.5):
    """Build a context of roughly target_tokens with the needle planted
    at needle_depth (0 = start, 1 = end). One distractor per ~400 tokens."""
    rng = random.Random(seed)
    filler = []
    total = 0
    n_distractors = max(1, int(target_tokens // 400))
    distractor_positions = sorted(rng.sample(range(40), min(n_distractors, 40)))
    i = 0
    sentences = []
    while total < target_tokens:
        if i in distractor_positions:
            s = rng.choice(DISTRACTORS)
        else:
            s = rng.choice(FILLER)
        sentences.append(s)
        total += _tokens_of(s)
        i += 1
    insert_at = int(len(sentences) * needle_depth)
    sentences.insert(insert_at, NEEDLE)
    return " ".join(sentences)


def needle_eval(sizes=(500, 1000, 2000, 4000, 8000), trials=5, seed=42):
    """At each context size, retrieve the chunk holding the needle with a
    TF-IDF-ish keyword scorer. Returns rows of hit@1 / hit@3."""
    query_terms = [w for w in WORD_RE.findall(QUERY.lower()) if w not in STOPWORDS]
    rows = []
    for size in sizes:
        hits1 = hits3 = 0
        for t in range(trials):
            ctx = build_context(size, seed * 1000 + size + t)
            words = ctx.split()
            chunks = _chunk_words(words)
            needle_idx = next(i for i, c in enumerate(chunks) if "84712" in c)
            df = {}
            for c in chunks:
                for w in set(WORD_RE.findall(c.lower())):
                    df[w] = df.get(w, 0) + 1
            n = len(chunks)
            idf = {w: math.log((n + 1) / (d + 0.5)) + 1 for w, d in df.items()}
            scored = sorted(
                range(len(chunks)),
                key=lambda i: _score_chunk(chunks[i], query_terms, idf),
                reverse=True,
            )
            if scored[0] == needle_idx:
                hits1 += 1
            if needle_idx in scored[:3]:
                hits3 += 1
        rows.append({
            "target_tokens": size,
            "trials": trials,
            "hit_at_1": round(hits1 / trials, 2),
            "hit_at_3": round(hits3 / trials, 2),
        })
    return rows


def format_eval(rows):
    lines = ["target_tokens  trials  hit@1  hit@3",
             "-----------------------------------"]
    for r in rows:
        lines.append(f"{r['target_tokens']:<14} {r['trials']:<7} "
                     f"{r['hit_at_1']:<6} {r['hit_at_3']}")
    lines.append("")
    lines.append("Retriever: TF-IDF-ish keyword scorer over ~150-word chunks, "
                 "query: 'What is the current vault passcode?'.")
    lines.append("Needle planted mid-context ('lost in the middle'); distractors "
                 "share the query words with a different, retired code.")
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check whether a prompt fits a model's effective context.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="check a prompt file against a model")
    p_check.add_argument("--model", required=True, help="model name (see: models)")
    p_check.add_argument("--file", required=True, help="prompt text file")
    p_check.add_argument("--effective-tokens", type=int, default=None,
                         help="override the model's effective context")
    p_check.add_argument("--price-per-1m", type=float, default=None,
                         help="override input price per 1M tokens (USD)")
    p_check.add_argument("--json", action="store_true", help="print JSON")

    p_eval = sub.add_parser("eval", help="run the needle-retrieval eval")
    p_eval.add_argument("--sizes", default="500,1000,2000,4000,8000",
                        help="comma-separated target token sizes")
    p_eval.add_argument("--trials", type=int, default=5)
    p_eval.add_argument("--seed", type=int, default=42)
    p_eval.add_argument("--json", action="store_true", help="print JSON")

    sub.add_parser("models", help="list built-in models")

    args = parser.parse_args(argv)
    models = load_models()

    if args.cmd == "models":
        for m in models.values():
            print(f"{m['name']:<22} advertised {m['advertised_tokens']:>8,}  "
                  f"effective {m['effective_tokens']:>8,}  "
                  f"${m['input_price_per_1m_usd']}/1M in")
        print("\nEffective tokens are conservative working estimates, not "
              "vendor claims. Override with --effective-tokens.")
        return 0

    if args.cmd == "check":
        if args.model not in models:
            print(f"Unknown model: {args.model}. Run 'models' to list them.",
                  file=sys.stderr)
            return 2
        text = Path(args.file).read_text(encoding="utf-8")
        result = check_prompt(text, models[args.model],
                              args.effective_tokens, args.price_per_1m)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(format_check(result))
        return 1 if result["verdict"] == "OVER" else 0

    if args.cmd == "eval":
        sizes = tuple(int(s) for s in args.sizes.split(","))
        rows = needle_eval(sizes=sizes, trials=args.trials, seed=args.seed)
        if args.json:
            print(json.dumps(rows, indent=2))
        else:
            print(format_eval(rows))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
