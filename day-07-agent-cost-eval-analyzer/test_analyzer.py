#!/usr/bin/env python3
"""Tests for analyzer.py. Run: python3 -m unittest test_analyzer -v"""
import json
import os
import tempfile
import unittest

from analyzer import load_runs, run_cost, summarise


def _run(**over):
    rec = {"task_id": "t", "harness": "h", "input_tokens": 10000,
           "cached_input_tokens": 8000, "output_tokens": 1000, "solved": True}
    rec.update(over)
    return rec


class TestCost(unittest.TestCase):
    def test_cached_tokens_priced_at_cached_rate(self):
        # (10000-8000)*3 + 8000*0.30 + 1000*15, all per 1M = $0.0234
        self.assertAlmostEqual(
            run_cost(_run(), {"input": 3.0, "cached": 0.30, "output": 15.0}),
            0.0234)

    def test_cost_per_solved_penalises_failed_tasks(self):
        prices = {"input": 3.0, "cached": 0.30, "output": 15.0}
        # Same per-task cost, but only 1 of 2 solved -> cost/solved doubles.
        runs = [_run(task_id="a", solved=True), _run(task_id="b", solved=False)]
        summary = summarise(runs, prices)[0]
        self.assertEqual(summary["solved"], 1)
        self.assertAlmostEqual(summary["cost_per_solved"],
                               2 * summary["cost_per_task"])

    def test_zero_solved_sorts_last_with_no_value(self):
        prices = {"input": 3.0, "cached": 0.30, "output": 15.0}
        runs = [_run(harness="winner", solved=True),
                _run(harness="loser", solved=False)]
        summaries = summarise(runs, prices)
        self.assertEqual(summaries[0]["harness"], "winner")
        self.assertIsNone(summaries[1]["cost_per_solved"])

    def test_malformed_lines_skipped_not_crash(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            fh.write(json.dumps(_run()) + "\n")
            fh.write("not json\n")
            fh.write(json.dumps({"task_id": "x"}) + "\n")  # missing fields
            path = fh.name
        try:
            runs, skipped = load_runs(path)
        finally:
            os.unlink(path)
        self.assertEqual(len(runs), 1)
        self.assertEqual(skipped, 2)

    def test_cache_hit_rate(self):
        prices = {"input": 3.0, "cached": 0.30, "output": 15.0}
        summary = summarise([_run()], prices)[0]
        self.assertAlmostEqual(summary["cache_hit_rate"], 0.8)


if __name__ == "__main__":
    unittest.main()
