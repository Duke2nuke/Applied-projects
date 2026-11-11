"""Tests for the Day 16 LangGraph RAG agent.

Run:  python -m unittest test_agent -v
"""

import json
import os
import unittest

from agent import build_graph, resume_question, run_question
from langgraph.types import Command
from retrieval import Retriever
from run import run_eval

BASE = os.path.dirname(os.path.abspath(__file__))


class TestRetriever(unittest.TestCase):
    def test_top_hit_is_the_right_doc(self):
        r = Retriever.from_file()
        hits = r.retrieve("Which 3D printers does ForgeLab have?")
        self.assertEqual(hits[0]["id"], "3d-printing")
        self.assertGreater(hits[0]["score"], 0.15)

    def test_out_of_scope_scores_low(self):
        r = Retriever.from_file()
        hits = r.retrieve("What is the capital of France?")
        self.assertLess(hits[0]["score"], 0.15)


class TestAgentGraph(unittest.TestCase):
    def test_answerable_question_answered(self):
        result, _, _ = run_question(
            "When does ForgeLab open on weekdays?", auto_approve=True,
            thread_id="test-answer",
        )
        self.assertEqual(result["decision"], "answered")
        self.assertIn("9am", result["answer"])
        self.assertIn("retrieve", result["trace"])
        self.assertIn("answer", result["trace"])

    def test_out_of_scope_refused_without_gate(self):
        result, _, _ = run_question(
            "What is the capital of France?", auto_approve=True,
            thread_id="test-refuse",
        )
        self.assertEqual(result["decision"], "refused")
        self.assertIn("Not found", result["answer"])
        self.assertNotIn("answer", result["trace"])

    def test_gate_pauses_and_resume_approve(self):
        result, graph, config = run_question(
            "Which 3D printers does ForgeLab have?", auto_approve=False,
            thread_id="test-gate-approve",
        )
        self.assertIn("__interrupt__", result)
        final = resume_question(graph, config, True)
        self.assertEqual(final["decision"], "answered")
        self.assertIn("Prusa", final["answer"])

    def test_gate_resume_decline_refuses(self):
        result, graph, config = run_question(
            "Which 3D printers does ForgeLab have?", auto_approve=False,
            thread_id="test-gate-decline",
        )
        self.assertIn("__interrupt__", result)
        final = resume_question(graph, config, False)
        self.assertEqual(final["decision"], "refused")
        self.assertIn("Not approved", final["answer"])

    def test_eval_metrics_are_sane(self):
        summary = run_eval(write_trace_log=False)
        self.assertEqual(summary["cases"], 10)
        self.assertGreaterEqual(summary["recall@1"], 0.75)
        self.assertEqual(summary["refusal_accuracy"], 1.0)
        self.assertTrue(os.path.exists(os.path.join(BASE, "eval_results.json")))


if __name__ == "__main__":
    unittest.main()
