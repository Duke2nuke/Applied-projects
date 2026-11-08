"""Tests for context_packer.py — run with: python3 test_context_packer.py"""

import unittest

from context_packer import (
    ContextItem,
    compact_history,
    estimate_tokens,
    pack,
)


def item(kind, text, priority=50, must_include=False, label=""):
    return ContextItem(kind, text, priority, must_include, label or kind)


class TestEstimateTokens(unittest.TestCase):
    def test_longer_text_costs_more(self):
        self.assertGreater(estimate_tokens("x" * 400), estimate_tokens("x" * 40))

    def test_empty_is_zero(self):
        self.assertEqual(estimate_tokens(""), 0)


class TestPack(unittest.TestCase):
    def test_budget_never_exceeded(self):
        items = [item("retrieved", "word " * 200, 90),
                 item("examples", "word " * 200, 80),
                 item("history", "word " * 200, 40)]
        result = pack(items, budget=100)
        self.assertLessEqual(result.tokens_used, 100)

    def test_must_include_always_kept(self):
        items = [item("system", "do this", 100, must_include=True),
                 item("retrieved", "word " * 500, 90)]
        result = pack(items, budget=50)
        kept_kinds = [d.item.kind for d in result.kept]
        self.assertIn("system", kept_kinds)
        self.assertEqual(result.kept[0].item.text, "do this")

    def test_drops_lowest_priority_first(self):
        items = [item("retrieved", "aaa " * 100, 90, label="high"),
                 item("retrieved", "bbb " * 100, 10, label="low"),
                 item("retrieved", "ccc " * 100, 50, label="mid")]
        result = pack(items, budget=150, policy="drop")
        dropped = [d.item.label for d in result.dropped]
        self.assertIn("low", dropped)
        self.assertNotIn("high", dropped)

    def test_truncate_policy_caps_long_item(self):
        items = [item("retrieved", "word " * 300, 90)]
        result = pack(items, budget=50, policy="truncate")
        self.assertEqual(len(result.dropped), 0)
        self.assertEqual(result.kept[0].action, "truncated")
        self.assertLessEqual(result.tokens_used, 50)

    def test_prompt_order_is_kind_order_not_priority(self):
        items = [item("history", "latest turn", 10),
                 item("system", "instructions", 100, must_include=True)]
        result = pack(items, budget=500)
        self.assertTrue(result.prompt.index("[SYSTEM]") < result.prompt.index("[HISTORY]"))

    def test_empty_input_gives_empty_prompt(self):
        result = pack([], budget=100)
        self.assertEqual(result.prompt, "")
        self.assertEqual(result.tokens_used, 0)

    def test_deterministic(self):
        items = [item("retrieved", "doc one " * 50, 70),
                 item("history", "turn one\nturn two", 40),
                 item("examples", "ex " * 50, 80)]
        first = pack(items, budget=120).prompt
        second = pack(items, budget=120).prompt
        self.assertEqual(first, second)


class TestCompactHistory(unittest.TestCase):
    def test_compaction_reduces_tokens_and_keeps_latest(self):
        turns = "\n".join(
            f"User: question number {i} about packing context into a budget."
            for i in range(6)
        ) + "\nAssistant: latest answer about the budget report."
        hist = item("history", turns, 40)
        compacted = compact_history(hist, max_tokens=40)
        self.assertLess(compacted.tokens, hist.tokens)
        self.assertIn("latest answer about the budget report", compacted.text)

    def test_compact_policy_uses_compaction_before_dropping(self):
        turns = "\n".join(
            f"Turn {i}: a fairly long exchange about context engineering and budgets."
            for i in range(8)
        )
        items = [item("system", "instructions", 100, must_include=True),
                 item("history", turns, 40)]
        result = pack(items, budget=80, policy="compact")
        actions = [d.action for d in result.kept]
        self.assertIn("compacted", actions)
        self.assertEqual(len(result.dropped), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
