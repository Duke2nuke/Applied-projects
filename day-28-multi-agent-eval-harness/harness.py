"""Multi-agent eval harness: run agent strategies over a golden set,
grade them deterministically, and emit a comparison plus traces.

Usage:
    python3 harness.py
    python3 harness.py --agents direct,planner
    python3 harness.py --fail-under 0.7
    python3 harness.py --format json --out results.json --traces traces.jsonl

Exit code: 0 if every agent's mean correctness is >= --fail-under
(default 0.7), else 1. That is the regression gate: wire it into CI
and a prompt/model change that drops an agent below the bar fails
the build instead of shipping silently.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from agents import AGENTS, Tracer
from graders import grade, mean
from model import Model, load_default_store

HERE = Path(__file__).parent


def load_golden(path=HERE / "golden.json"):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def run_eval(agent_names, cases, store):
    model = Model(store)
    tracer = Tracer()
    per_agent = {}
    for name in agent_names:
        agent = AGENTS[name](model)
        scored = []
        total_ms = 0.0
        span_mark = len(tracer.spans)
        for case in cases:
            start = time.perf_counter()
            result = agent.run(case["question"], tracer)
            total_ms += (time.perf_counter() - start) * 1000
            scores = grade(result, case)
            scores["task_id"] = case["id"]
            scores["category"] = case["category"]
            scored.append(scores)
        # Tokens are counted from spans added during this agent's runs,
        # so debate is charged for its proposer's draft spans too.
        total_tokens = sum(
            s.get("tokens_in", 0) + s.get("tokens_out", 0)
            for s in tracer.spans[span_mark:])
        per_agent[name] = {
            "mean_correctness": mean(scored, "correctness"),
            "mean_grounded": mean(scored, "grounded"),
            "mean_concise": mean(scored, "concise"),
            "mean_latency_ms": round(total_ms / len(cases), 2) if cases else 0,
            "total_tokens_est": total_tokens,
            "by_category": {
                cat: mean([s for s in scored if s["category"] == cat],
                          "correctness")
                for cat in sorted({s["category"] for s in scored})
            },
            "per_task": scored,
        }
    return per_agent, tracer.spans


def print_table(per_agent, n_cases):
    header = f"{'agent':<9}{'correct':>9}{'grounded':>10}{'concise':>9}{'ms/task':>9}{'tokens*':>9}"
    print(f"Golden set: {n_cases} cases (4 simple, 4 two-part, 4 distractor)")
    print(header)
    print("-" * len(header))
    for name, s in per_agent.items():
        print(f"{name:<9}{s['mean_correctness']:>9.3f}{s['mean_grounded']:>10.3f}"
              f"{s['mean_concise']:>9.3f}{s['mean_latency_ms']:>9.2f}"
              f"{s['total_tokens_est']:>9d}")
    print("* tokens are estimates (words x 1.3), not a real tokenizer count.")
    for name, s in per_agent.items():
        cats = ", ".join(f"{c}={v:.2f}" for c, v in s["by_category"].items())
        print(f"  {name}: {cats}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents", default="direct,planner,debate",
                        help="comma-separated agent names")
    parser.add_argument("--golden", default=str(HERE / "golden.json"))
    parser.add_argument("--fail-under", type=float, default=0.7,
                        help="regression gate: fail if any agent scores below this")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--out", default=str(HERE / "results.json"))
    parser.add_argument("--traces", default=str(HERE / "traces.jsonl"))
    args = parser.parse_args(argv)

    names = [n.strip() for n in args.agents.split(",") if n.strip()]
    unknown = [n for n in names if n not in AGENTS]
    if unknown:
        print(f"unknown agent(s): {', '.join(unknown)} "
              f"(choose from {', '.join(AGENTS)})", file=sys.stderr)
        return 2
    cases = load_golden(args.golden)
    per_agent, spans = run_eval(names, cases, load_default_store())

    summary = {name: {k: v for k, v in s.items() if k != "per_task"}
               for name, s in per_agent.items()}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"agents": per_agent, "n_cases": len(cases)},
                  fh, indent=2)
    with open(args.traces, "w", encoding="utf-8") as fh:
        for span in spans:
            fh.write(json.dumps(span) + "\n")

    if args.format == "json":
        print(json.dumps(summary, indent=2))
    else:
        print_table(per_agent, len(cases))

    failing = [n for n, s in per_agent.items()
               if s["mean_correctness"] < args.fail_under]
    if failing:
        print(f"GATE FAILED: {', '.join(failing)} below {args.fail_under}",
              file=sys.stderr)
        return 1
    print(f"Gate passed: every agent >= {args.fail_under} correctness.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
