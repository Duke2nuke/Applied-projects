"""Layered guardrails for a demo LLM support bot (stdlib only).

Three layers, mirroring what production stacks do (NeMo Guardrails,
Guardrails AI, Llama Guard) at a fraction of the scale:

  1. input  - block prompt injection / jailbreaks, redact PII, cap abuse
  2. tool   - authorise tool calls (a refund needs a real order + a
              sane amount, not just the words "refund this")
  3. output - block secret leakage, redact PII, check stated facts
              against ground truth, cap unbounded output

Everything here is pattern-based and demo-scale: it shows the shape of
a guardrail pipeline and, more importantly, how to *measure* one. Real
deployments add a classifier judge (e.g. Llama Guard) in front of the
same pipeline — the checks here are the deterministic floor, not the
ceiling.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Demo secrets the vulnerable bot holds. Fake values, used only so the
# red-team run can prove a leak happened. Never put real secrets here.
DEMO_SECRETS = [
    "REFUND-2026-VIP",  # internal refund code in the bot's system prompt
    "admin-hunter2",    # admin password in the bot's system prompt
]

KNOWN_ORDERS = {"ORD-1001", "ORD-1002", "ORD-1003"}
MAX_REFUND = 5000        # rupees; anything above needs a human
MAX_REPEAT = 50          # "repeat X N times" is capped
MAX_INPUT_CHARS = 2000
MAX_OUTPUT_CHARS = 2000

# Ground truth the output checker can verify (demo-scale).
# A real system would check against a knowledge base; the shape is
# the same: claims that contradict known facts get blocked.
FACT_CONTRADICTIONS = [
    (re.compile(r"warranty[^.]{0,40}5\s*years", re.I),
     "claims a 5-year warranty (real warranty is 1 year)"),
    (re.compile(r"store\s+is\s+closing\s+tomorrow", re.I),
     "claims the store is closing tomorrow (it is not closing)"),
]

# --- input patterns -------------------------------------------------------

INJECTION_PATTERNS = [
    (re.compile(r"ignore\s+(all\s+)?(previous|prior|above|your)\s+instructions", re.I),
     "tells the model to ignore its instructions"),
    (re.compile(r"disregard\s+(your\s+)?(instructions|system\s+prompt|rules)", re.I),
     "tells the model to disregard its instructions"),
    (re.compile(r"forget\s+(your\s+)?(instructions|rules|system\s+prompt)", re.I),
     "tells the model to forget its instructions"),
    (re.compile(r"repeat\s+(your\s+)?(system\s+prompt|instructions|initial\s+prompt)", re.I),
     "asks the model to repeat its system prompt"),
    (re.compile(r"(what\s+(is|are)|show\s+(me\s+)?|reveal\s+)(your\s+)?(system\s+prompt|instructions|initial\s+prompt)", re.I),
     "asks for the system prompt / instructions"),
    (re.compile(r"reveal\s+(your\s+)?(secret|password|refund\s+code)", re.I),
     "asks the model to reveal a secret"),
    (re.compile(r"\bDAN\b|developer\s+mode|jailbreak", re.I),
     "jailbreak / DAN-style override"),
    (re.compile(r"you\s+are\s+now\s+|pretend\s+(you\s+are|to\s+be)\s+", re.I),
     "roleplay override of the model's identity"),
    (re.compile(r"override\s+(your\s+)?(instructions|rules|safety)", re.I),
     "asks the model to override its rules"),
    (re.compile(r"(system|admin|support)\s+note\s*:", re.I),
     "embedded 'note from system/admin' — indirect injection"),
]

PII_PATTERNS = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
     "email address"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "card-like number"),
    (re.compile(r"\b[6-9]\d{9}\b"), "10-digit phone number"),
]

REPEAT_PATTERN = re.compile(r"repeat\s+.{0,30}?(\d+)\s+times", re.I)


@dataclass
class Verdict:
    """One guardrail decision."""
    decision: str          # "allow" | "block" | "redact"
    reason: str = ""       # human-readable why
    category: str = ""     # OWASP LLM Top 10 id, e.g. "LLM01"
    cleaned: str = ""      # text after redaction (only for "redact")


def check_input(text: str) -> Verdict:
    """Layer 1: screen the user's prompt before the bot sees it."""
    if len(text) > MAX_INPUT_CHARS:
        return Verdict("block", f"input is {len(text)} chars (limit "
                       f"{MAX_INPUT_CHARS})", "LLM10")

    for pattern, why in INJECTION_PATTERNS:
        if pattern.search(text):
            return Verdict("block",
                           f"prompt-injection pattern: {why}", "LLM01")

    match = REPEAT_PATTERN.search(text)
    if match and int(match.group(1)) > MAX_REPEAT:
        return Verdict("block",
                       f"asks for {match.group(1)} repetitions "
                       f"(limit {MAX_REPEAT})", "LLM10")

    cleaned = text
    found = []
    for pattern, why in PII_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub("[REDACTED]", cleaned)
            found.append(why)
    if found:
        return Verdict("redact",
                       "redacted PII from input: " + ", ".join(found),
                       "LLM02", cleaned=cleaned)

    return Verdict("allow")


def check_output(text: str, action: dict | None) -> Verdict:
    """Layers 2 + 3: screen the bot's answer (and its tool call)."""
    for secret in DEMO_SECRETS:
        if secret in text:
            return Verdict("block",
                           "output leaks an internal secret", "LLM07")

    if action and action.get("tool") == "issue_refund":
        order = action.get("order_id", "")
        amount = action.get("amount", 0)
        if order not in KNOWN_ORDERS:
            return Verdict("block",
                           f"refund for unknown order {order} — no such "
                           "order exists", "LLM06")
        if amount > MAX_REFUND:
            return Verdict("block",
                           f"refund of {amount} exceeds the {MAX_REFUND} "
                           "auto-approval limit — needs a human", "LLM06")

    for pattern, why in FACT_CONTRADICTIONS:
        if pattern.search(text):
            return Verdict("block",
                           f"output states a false fact: {why}", "LLM09")

    if len(text) > MAX_OUTPUT_CHARS:
        return Verdict("block",
                       f"output is {len(text)} chars (limit "
                       f"{MAX_OUTPUT_CHARS})", "LLM10")

    cleaned = text
    found = []
    for pattern, why in PII_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub("[REDACTED]", cleaned)
            found.append(why)
    if found:
        return Verdict("redact",
                       "redacted PII from output: " + ", ".join(found),
                       "LLM02", cleaned=cleaned)

    return Verdict("allow")
