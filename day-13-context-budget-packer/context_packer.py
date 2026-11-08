"""Context Budget Packer — context engineering for LLM calls.

Context engineering is the skill of deciding exactly what a model sees
on each call: instructions, examples, retrieved documents, tool results
and conversation history, fitted into a fixed token budget. This module
does that packing deterministically, with no model API and no downloads.

It answers three questions every agent builder hits in production:
  1. What do I keep when the context does not fit the budget?
  2. How do I shrink history without losing the latest turns?
  3. Can I prove, before calling the model, what was kept and dropped?

Python standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field

# Order in which kinds appear in the assembled prompt. System
# instructions first, then examples, then retrieved facts, then tool
# results, then the most recent conversation — the order most agent
# prompts use, and the order a model reads best.
KIND_ORDER = ["system", "examples", "retrieved", "tool_result", "history"]

# Characters per token for the estimate. Real tokenisers differ per
# model (roughly 3-5 chars/token for English prose); 4 is a common
# rule of thumb and is labelled an estimate everywhere it appears.
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Rough token estimate: len(text) / 4, rounded up.

    This is NOT a real tokenizer — it under- or over-counts for code,
    non-English text and long words. It is good enough to compare
    packing policies and to stay safely under a budget; for a real
    model call, replace it with that model's tokenizer.
    """
    if not text:
        return 0
    return max(1, -(-len(text) // CHARS_PER_TOKEN))


def first_sentence(text: str) -> str:
    """First sentence of a text, or the first 120 chars if none ends."""
    text = " ".join(text.split())
    match = re.search(r"[.!?]\s", text)
    if match:
        return text[: match.end()].strip()
    return text[:120].strip()


@dataclass
class ContextItem:
    """One candidate piece of context for a single model call."""

    kind: str                      # system | examples | retrieved | tool_result | history
    text: str
    priority: int = 50             # 0-100; higher is kept first
    must_include: bool = False     # always kept, even over budget
    label: str = ""                # short name shown in reports

    def __post_init__(self) -> None:
        if self.kind not in KIND_ORDER:
            raise ValueError(f"unknown kind {self.kind!r}; use one of {KIND_ORDER}")
        self.priority = max(0, min(100, self.priority))
        if not self.label:
            self.label = f"{self.kind}:{self.text[:24].strip()}"

    @property
    def tokens(self) -> int:
        return estimate_tokens(self.text)


@dataclass
class PackDecision:
    item: ContextItem
    action: str                    # kept | dropped | truncated | compacted
    tokens_used: int
    note: str = ""


@dataclass
class PackResult:
    prompt: str
    decisions: list[PackDecision] = field(default_factory=list)
    budget: int = 0

    @property
    def tokens_used(self) -> int:
        return sum(d.tokens_used for d in self.decisions if d.action != "dropped")

    @property
    def tokens_requested(self) -> int:
        return sum(d.item.tokens for d in self.decisions)

    @property
    def kept(self) -> list[PackDecision]:
        return [d for d in self.decisions if d.action != "dropped"]

    @property
    def dropped(self) -> list[PackDecision]:
        return [d for d in self.decisions if d.action == "dropped"]

    def report(self) -> str:
        lines = [
            f"Budget: {self.budget} tokens (estimate) | "
            f"requested: {self.tokens_requested} | used: {self.tokens_used} "
            f"({100 * self.tokens_used // max(1, self.budget)}% of budget)",
            f"Kept {len(self.kept)}, dropped {len(self.dropped)}.",
        ]
        for d in self.decisions:
            mark = {"kept": "[keep]", "dropped": "[drop]",
                    "truncated": "[trim]", "compacted": "[pack]"}[d.action]
            lines.append(
                f"  {mark} {d.item.label} ({d.item.kind}, prio {d.item.priority}): "
                f"{d.item.tokens} -> {d.tokens_used} tokens"
                + (f" — {d.note}" if d.note else "")
            )
        return "\n".join(lines)


def compact_history(item: ContextItem, max_tokens: int) -> ContextItem:
    """Shrink a history item to an extractive summary under max_tokens.

    Keeps the first sentence of each turn and the full text of the
    most recent turn, so the model still sees what was just said.
    Returns a new item; the original is untouched.
    """
    turns = [t.strip() for t in item.text.split("\n") if t.strip()]
    if not turns:
        return ContextItem(item.kind, "", item.priority, item.must_include, item.label)
    latest = turns[-1]
    summary_lines = [f"[earlier] {first_sentence(t)}" for t in turns[:-1]]
    compacted = "\n".join(summary_lines + [latest])
    if estimate_tokens(compacted) > max_tokens and len(summary_lines) > 1:
        # Still too big: keep only the latest turn plus one summary line.
        compacted = "\n".join(summary_lines[:1] + [latest])
    if estimate_tokens(compacted) > max_tokens:
        compacted = latest[: max_tokens * CHARS_PER_TOKEN]
    return ContextItem(item.kind, compacted, item.priority,
                       item.must_include, item.label + " (compacted)")


def pack(items: list[ContextItem], budget: int,
         policy: str = "compact") -> PackResult:
    """Fit context items into a token budget.

    Policies for overflow, in order of how much they preserve:
      compact   — compact history items first, then truncate long
                  items, then drop lowest priority (default).
      truncate  — truncate long items to a per-item cap, then drop.
      drop      — drop whole items, lowest priority first.

    Must-include items are always kept; if they alone exceed the
    budget they are truncated to fit and the overrun is reported.
    The returned prompt orders kept items by kind, not by priority,
    so the model reads a coherent prompt.
    """
    if budget <= 0:
        raise ValueError("budget must be positive")
    if policy not in ("compact", "truncate", "drop"):
        raise ValueError(f"unknown policy {policy!r}")

    decisions: list[PackDecision] = []
    must = [i for i in items if i.must_include]
    rest = [i for i in items if not i.must_include]
    # Fill order: highest priority first; ties broken by fewer tokens
    # (more value per token) and then by kind order, for determinism.
    rest.sort(key=lambda i: (-i.priority, i.tokens, KIND_ORDER.index(i.kind)))

    remaining = budget
    kept: list[ContextItem] = []

    def keep(prompt_item: ContextItem, action: str, note: str = "",
             original: ContextItem | None = None) -> None:
        """Record a kept item. The decision keeps the ORIGINAL item (so
        the report shows requested -> used tokens); the prompt gets the
        possibly trimmed/compacted text."""
        nonlocal remaining
        used = prompt_item.tokens
        decisions.append(PackDecision(original or prompt_item, action, used, note))
        kept.append(prompt_item)
        remaining -= used

    # 1. Must-include items always go in; truncate them only if they
    #    alone would blow the budget.
    for item in must:
        if item.tokens <= remaining:
            keep(item, "kept")
        else:
            cap = max(remaining, 1)
            trimmed = item.text[: cap * CHARS_PER_TOKEN].rstrip()
            keep(ContextItem(item.kind, trimmed, item.priority, True,
                             item.label + " (trimmed)"),
                 "truncated", f"must-include exceeded budget, cut to {cap} tokens",
                 original=item)
    # 2. Optional items, in priority order.
    for item in rest:
        if item.tokens <= remaining:
            keep(item, "kept")
            continue
        if policy == "compact" and item.kind == "history":
            compacted = compact_history(item, remaining)
            if compacted.tokens <= remaining and compacted.text.strip():
                keep(compacted, "compacted",
                     f"history compacted {item.tokens} -> {compacted.tokens} tokens",
                     original=item)
                continue
        if policy in ("compact", "truncate"):
            cap = max(remaining, 1)
            trimmed = item.text[: cap * CHARS_PER_TOKEN].rstrip()
            if trimmed and estimate_tokens(trimmed) <= remaining:
                keep(ContextItem(item.kind, trimmed, item.priority, False,
                                 item.label + " (trimmed)"),
                     "truncated", f"cut to fit remaining {remaining} tokens",
                     original=item)
                continue
        decisions.append(PackDecision(item, "dropped", 0,
                                      f"needs {item.tokens} tokens, {remaining} left"))

    # 3. Assemble the prompt in kind order (system first, history last).
    kept.sort(key=lambda i: (KIND_ORDER.index(i.kind), -i.priority))
    sections = []
    for item in kept:
        sections.append(f"[{item.kind.upper()}] {item.text}")
    return PackResult(prompt="\n\n".join(sections), decisions=decisions, budget=budget)


def load_items(path: str) -> list[ContextItem]:
    """Load context items from a JSON file: {"budget": N, "items": [...]}."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [ContextItem(**entry) for entry in data["items"]], data.get("budget", 1000)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pack context items into a token budget (context engineering).")
    parser.add_argument("context_file", help="JSON file with budget + items")
    parser.add_argument("--budget", type=int, default=None,
                        help="override the budget in the file")
    parser.add_argument("--policy", choices=["compact", "truncate", "drop"],
                        default="compact", help="overflow policy (default: compact)")
    parser.add_argument("--prompt-only", action="store_true",
                        help="print only the packed prompt, no report")
    args = parser.parse_args(argv)

    items, file_budget = load_items(args.context_file)
    budget = args.budget or file_budget
    result = pack(items, budget, args.policy)
    if args.prompt_only:
        print(result.prompt)
    else:
        print(result.prompt)
        print("\n--- budget report ---")
        print(result.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
