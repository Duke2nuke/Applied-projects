"""Tests for the multi-agent eval harness. Run: python3 -m unittest -v"""

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents import AGENTS, DebateAgent, DirectAgent, PlannerAgent, Tracer, split_parts
from graders import grade
from harness import load_golden, main, run_eval
from model import Model, content_words, load_default_store

HERE = Path(__file__).parent


def case(qid):
    return next(c for c in load_golden() if c["id"] == qid)


class FakeResult:
    def __init__(self, answer, cited):
        self.answer = answer
        self.cited = cited


class TestGraders(unittest.TestCase):
    def test_full_credit(self):
        s = grade(FakeResult("Mars is known as the Red Planet. [f01]", ["f01"]), case("q01"))
        self.assertEqual(s, {"correctness": 1.0, "grounded": 1.0, "concise": 1.0})

    def test_partial_credit(self):
        s = grade(FakeResult("Jupiter is the largest planet. [f02]", ["f02", "f03"]), case("q05"))
        self.assertEqual(s["correctness"], 0.5)
        self.assertEqual(s["grounded"], 1.0)

    def test_wrong_citation_fails_grounded(self):
        s = grade(FakeResult("The Pacific Ocean is the largest. [f14]", ["f14"]), case("q09"))
        self.assertEqual(s["correctness"], 0.0)
        self.assertEqual(s["grounded"], 0.0)

    def test_long_answer_fails_concise(self):
        s = grade(FakeResult("word " * 41, ["f01"]), case("q01"))
        self.assertEqual(s["concise"], 0.0)


class TestRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = load_default_store()

    def test_naive_retrieval_falls_for_distractor(self):
        fact, _ = self.store.naive_retrieve("Which planet is the largest?")
        self.assertEqual(fact["id"], "f14")  # Pacific Ocean out-scores Jupiter

    def test_content_retrieval_picks_right_fact(self):
        fact, _ = self.store.content_retrieve("Which planet is the largest?")
        self.assertEqual(fact["id"], "f02")

    def test_content_words_drop_superlatives(self):
        self.assertNotIn("largest", content_words("Which planet is the largest?"))
        self.assertIn("planet", content_words("Which planet is the largest?"))


class TestAgents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = Model(load_default_store())

    def test_direct_gets_simple_question(self):
        r = DirectAgent(self.model).run(case("q01")["question"], Tracer())
        self.assertEqual(grade(r, case("q01"))["correctness"], 1.0)

    def test_direct_fails_distractor(self):
        r = DirectAgent(self.model).run(case("q09")["question"], Tracer())
        self.assertEqual(grade(r, case("q09"))["correctness"], 0.0)

    def test_planner_answers_both_parts(self):
        r = PlannerAgent(self.model).run(case("q05")["question"], Tracer())
        self.assertEqual(grade(r, case("q05"))["correctness"], 1.0)

    def test_planner_resolves_pronoun_with_context(self):
        # 'its largest moon' must resolve to Jupiter's moon, not Earth's.
        r = PlannerAgent(self.model).run(case("q05")["question"], Tracer())
        self.assertIn("Ganymede", r.answer)

    def test_debate_corrects_distractor(self):
        r = DebateAgent(self.model).run(case("q09")["question"], Tracer())
        self.assertEqual(grade(r, case("q09"))["correctness"], 1.0)

    def test_split_parts(self):
        self.assertEqual(len(split_parts("A, and B")), 2)
        self.assertEqual(len(split_parts("Just one question?")), 1)


class TestHarness(unittest.TestCase):
    def test_direct_scores_below_planner(self):
        cases = load_golden()
        per_agent, _ = run_eval(["direct", "planner"], cases, load_default_store())
        self.assertLess(per_agent["direct"]["mean_correctness"],
                        per_agent["planner"]["mean_correctness"])

    def test_traces_are_well_formed(self):
        _, spans = run_eval(["debate"], load_golden(), load_default_store())
        self.assertTrue(spans)
        for span in spans:
            self.assertIn("trace_id", span)
            self.assertIn("span_id", span)
            self.assertIn("duration_ms", span)
            self.assertGreaterEqual(span["duration_ms"], 0)
        # Debate's draft spans share the debate trace id (no orphans).
        # One root span (no parent) per task; the proposer's nested
        # agent.run span is a child of the debate root, not a new root.
        root_spans = [s for s in spans if s["parent_span_id"] is None]
        self.assertEqual(len(root_spans), 12)
        child_trace_ids = {s["trace_id"] for s in spans if s["name"] != "agent.run"}
        self.assertTrue(child_trace_ids <= {s["trace_id"] for s in root_spans})

    def test_gate_fails_when_threshold_too_high(self):
        out, traces = HERE / "tmp_results.json", HERE / "tmp_traces.jsonl"
        try:
            rc = main(["--fail-under", "0.99", "--out", str(out),
                       "--traces", str(traces)])
            self.assertEqual(rc, 1)
            rc = main(["--fail-under", "0.5", "--out", str(out),
                       "--traces", str(traces)])
            self.assertEqual(rc, 0)
        finally:
            for p in (out, traces):
                if p.exists():
                    p.unlink()

    def test_unknown_agent_rejected(self):
        self.assertEqual(main(["--agents", "nope"]), 2)


if __name__ == "__main__":
    unittest.main()
