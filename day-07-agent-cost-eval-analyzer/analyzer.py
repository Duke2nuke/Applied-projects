#!/usr/bin/env python3
"""Agent-run cost & eval analyser (stdlib only).

Reads JSON Lines of agent runs and reports, per harness, the metric
that the current agent-engineering discussion centres on: cost per
SOLVED task -- not cost per token, and not a raw model leaderboard
score. A harness that burns tokens on failed tasks looks cheap per
token and expensive per solved task, which is exactly the difference
this tool makes visible.

Input record (one JSON object per line):
    {
      "task_id": "t1",
      "harness": "harness-a",
      "model": "demo-model",
      "input_tokens": 10000,          # total input tokens, incl. cached
      "cached_input_tokens": 8000,    # subset of input_tokens served from cache
      "output_tokens": 2000,
      "solved": true,
      "steps": 12,
      "tool_calls": 5,
      "duration_s": 45
    }

Pricing is per 1M tokens and is supplied on the command line, because
real prices differ by model and change often. Defaults are illustrative
only -- they are NOT any provider's real price list:
    input $3.00 / cached input $0.30 / output $15.00 per 1M tokens.

Usage:
    python3 analyzer.py sample_runs.jsonl
    python3 analyzer.py runs.jsonl --format json
    python3 analyzer.py runs.jsonl --input-price 1.0 --cached-price 0.1 --output-price 5.0
"""

import argparse
import json
import sys
from collections import defaultdict


def run_cost(run, prices):
    """Cost of one run in dollars. cached tokens are a subset of input."""
    uncached = max(0, run["input_tokens"] - run["cached_input_tokens"])
    return (
        uncached * prices["input"]
        + run["cached_input_tokens"] * prices["cached"]
        + run["output_tokens"] * prices["output"]
    ) / 1_000_000


def load_runs(path):
    runs, skipped = [], 0
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                # Validate the fields the maths needs; anything else
                # is a malformed log line, not a run.
                for key in ("task_id", "harness", "input_tokens",
                            "cached_input_tokens", "output_tokens", "solved"):
                    if key not in rec:
                        raise ValueError(f"missing field {key}")
                if rec["cached_input_tokens"] > rec["input_tokens"]:
                    raise ValueError("cached_input_tokens exceeds input_tokens")
                runs.append(rec)
            except (json.JSONDecodeError, ValueError) as exc:
                print(f"warning: skipping line {lineno}: {exc}", file=sys.stderr)
                skipped += 1
    return runs, skipped


def summarise(runs, prices):
    """Per-harness summary dicts, sorted by cost per solved task (best first).

    A harness with zero solved tasks has no cost-per-solved value, so
    it sorts last rather than being reported as $0.
    """
    by_harness = defaultdict(list)
    for run in runs:
        by_harness[run["harness"]].append(run)

    summaries = []
    for harness, hs_runs in by_harness.items():
        solved = sum(1 for r in hs_runs if r["solved"])
        total_cost = sum(run_cost(r, prices) for r in hs_runs)
        total_in = sum(r["input_tokens"] for r in hs_runs)
        total_out = sum(r["output_tokens"] for r in hs_runs)
        total_cached = sum(r["cached_input_tokens"] for r in hs_runs)
        n = len(hs_runs)
        summaries.append({
            "harness": harness,
            "tasks": n,
            "solved": solved,
            "success_rate": solved / n if n else 0.0,
            "total_cost": total_cost,
            "cost_per_task": total_cost / n if n else 0.0,
            "cost_per_solved": total_cost / solved if solved else None,
            "tokens_per_solved": (total_in + total_out) / solved if solved else None,
            "cache_hit_rate": total_cached / total_in if total_in else 0.0,
            "avg_steps": sum(r.get("steps", 0) for r in hs_runs) / n if n else 0.0,
            "avg_tool_calls": sum(r.get("tool_calls", 0) for r in hs_runs) / n if n else 0.0,
            "avg_duration_s": sum(r.get("duration_s", 0) for r in hs_runs) / n if n else 0.0,
        })
    summaries.sort(key=lambda s: (s["cost_per_solved"] is None, s["cost_per_solved"]))
    return summaries


def fmt_money(value):
    return "n/a" if value is None else f"${value:.4f}"


def render_text(summaries, skipped):
    lines = []
    for s in summaries:
        lines.append(f"{s['harness']}: {s['solved']}/{s['tasks']} solved "
                     f"({s['success_rate']:.0%}), total {fmt_money(s['total_cost'])}, "
                     f"cost/task {fmt_money(s['cost_per_task'])}, "
                     f"cost/solved {fmt_money(s['cost_per_solved'])}, "
                     f"tokens/solved {s['tokens_per_solved']:.0f}" if s["tokens_per_solved"] is not None
                     else f"{s['harness']}: {s['solved']}/{s['tasks']} solved "
                     f"({s['success_rate']:.0%}), total {fmt_money(s['total_cost'])}, "
                     f"cost/task {fmt_money(s['cost_per_task'])}, "
                     f"cost/solved n/a (nothing solved), tokens/solved n/a")
        lines.append(f"    cache hit {s['cache_hit_rate']:.0%}, "
                     f"avg steps {s['avg_steps']:.1f}, "
                     f"avg tool calls {s['avg_tool_calls']:.1f}, "
                     f"avg duration {s['avg_duration_s']:.1f}s")
    if summaries:
        best = summaries[0]
        if best["cost_per_solved"] is not None:
            lines.append(f"\nCheapest per solved task: {best['harness']} "
                         f"at {fmt_money(best['cost_per_solved'])}")
    if skipped:
        lines.append(f"\nSkipped {skipped} malformed log line(s).")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyse agent-run costs per solved task.")
    parser.add_argument("runs_file", help="JSON Lines file of agent runs")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--input-price", type=float, default=3.0,
                        help="dollars per 1M uncached input tokens (default 3.0)")
    parser.add_argument("--cached-price", type=float, default=0.30,
                        help="dollars per 1M cached input tokens (default 0.30)")
    parser.add_argument("--output-price", type=float, default=15.0,
                        help="dollars per 1M output tokens (default 15.0)")
    args = parser.parse_args(argv)
    prices = {"input": args.input_price, "cached": args.cached_price,
              "output": args.output_price}
    runs, skipped = load_runs(args.runs_file)
    if not runs:
        print("no valid runs found", file=sys.stderr)
        return 1
    summaries = summarise(runs, prices)
    if args.format == "json":
        print(json.dumps({"harnesses": summaries, "skipped_lines": skipped}, indent=2))
    else:
        print(render_text(summaries, skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
