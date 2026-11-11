"""CLI for the Day 16 LangGraph RAG agent.

Usage:
    python run.py "When does ForgeLab open on weekdays?"
    python run.py "Which 3D printers does ForgeLab have?" --auto-approve
    python run.py --eval            # 10-case golden-set eval -> eval_results.json
    python run.py --eval --no-trace # skip writing traces.jsonl

Without --auto-approve the graph pauses at the human gate and asks on the
terminal; answer y/n to resume. Every run appends one JSONL line to
traces.jsonl (question, nodes visited, top score, decision, latency).
"""

import argparse
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import build_graph, resume_question, run_question  # noqa: E402
from langgraph.types import Command  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
TRACE_PATH = os.path.join(BASE, "traces.jsonl")
EVAL_PATH = os.path.join(BASE, "eval.json")
RESULTS_PATH = os.path.join(BASE, "eval_results.json")


def write_trace(record):
    with open(TRACE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def ask_once(question, auto_approve, thread_id):
    """Run one question; handles the interactive gate. Returns final state."""
    started = time.time()
    result, graph, config = run_question(
        question, auto_approve=auto_approve, thread_id=thread_id
    )
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print("HUMAN GATE — the agent wants approval before answering:")
        print(f"  Question: {payload['question']}")
        print(f"  Draft (from {payload['source']}): {payload['draft_answer']}")
        reply = input("Approve this answer? [y/n] ").strip().lower()
        approve = reply in ("y", "yes")
        result = resume_question(graph, config, approve)
    latency_ms = round((time.time() - started) * 1000, 1)
    record = {
        "thread_id": thread_id,
        "question": question,
        "nodes": result.get("trace", []),
        "top_score": round(result.get("top_score", 0.0), 4),
        "decision": result.get("decision", ""),
        "approved": result.get("approved"),
        "latency_ms": latency_ms,
    }
    return result, record


def run_eval(write_trace_log=True):
    with open(EVAL_PATH, encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    per_case = []
    recall1_hits = 0
    recall3_hits = 0
    answered_correct = 0
    refused_correct = 0
    answerable = 0
    oos = 0
    for i, case in enumerate(cases):
        result, record = ask_once(
            case["question"], auto_approve=True, thread_id=f"eval-{i}"
        )
        retrieved_ids = [r["id"] for r in result.get("retrieved", [])]
        entry = {
            "question": case["question"],
            "decision": result.get("decision"),
            "top_score": record["top_score"],
            "retrieved": retrieved_ids,
            "nodes": record["nodes"],
        }
        if case.get("out_of_scope"):
            oos += 1
            ok = result.get("decision") == "refused"
            refused_correct += int(ok)
            entry["expected"] = "refused"
            entry["correct"] = ok
        else:
            answerable += 1
            recall1 = retrieved_ids and retrieved_ids[0] == case["expected_doc"]
            recall3 = case["expected_doc"] in retrieved_ids
            recall1_hits += int(bool(recall1))
            recall3_hits += int(bool(recall3))
            kw_ok = case["expected_keyword"].lower() in result.get("answer", "").lower()
            answered_correct += int(kw_ok and result.get("decision") == "answered")
            entry["expected_doc"] = case["expected_doc"]
            entry["recall@1"] = bool(recall1)
            entry["recall@3"] = bool(recall3)
            entry["keyword_in_answer"] = kw_ok
            entry["correct"] = bool(kw_ok and result.get("decision") == "answered")
        per_case.append(entry)
        if write_trace_log:
            write_trace(record)
    summary = {
        "cases": len(cases),
        "answerable": answerable,
        "out_of_scope": oos,
        "recall@1": round(recall1_hits / answerable, 3) if answerable else 0,
        "recall@3": round(recall3_hits / answerable, 3) if answerable else 0,
        "answer_accuracy": round(answered_correct / answerable, 3) if answerable else 0,
        "refusal_accuracy": round(refused_correct / oos, 3) if oos else 0,
        "per_case": per_case,
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Day 16 LangGraph RAG agent")
    parser.add_argument("question", nargs="?", help="question to ask the agent")
    parser.add_argument("--auto-approve", action="store_true",
                        help="skip the human approval gate")
    parser.add_argument("--eval", action="store_true",
                        help="run the 10-case golden-set eval")
    parser.add_argument("--no-trace", action="store_true",
                        help="do not append to traces.jsonl")
    args = parser.parse_args()

    if args.eval:
        summary = run_eval(write_trace_log=not args.no_trace)
        print(f"Eval: {summary['cases']} cases "
              f"({summary['answerable']} answerable, {summary['out_of_scope']} out-of-scope)")
        print(f"  recall@1 = {summary['recall@1']}")
        print(f"  recall@3 = {summary['recall@3']}")
        print(f"  answer accuracy = {summary['answer_accuracy']}")
        print(f"  refusal accuracy = {summary['refusal_accuracy']}")
        print(f"Results written to {RESULTS_PATH}")
        return 0

    if not args.question:
        parser.error("give a question, or use --eval")

    thread_id = f"cli-{uuid.uuid4().hex[:8]}"
    result, record = ask_once(args.question, args.auto_approve, thread_id)
    if not args.no_trace:
        write_trace(record)
    print()
    print(result.get("answer", ""))
    print(f"\n[decision={result.get('decision')} "
          f"nodes={' -> '.join(record['nodes'])} "
          f"top_score={record['top_score']} latency={record['latency_ms']}ms]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
