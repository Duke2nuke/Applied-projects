"""Three agent strategies over the same stub model, with tracing.

Every run emits OpenTelemetry-style spans (JSONL): one root span per
(task, agent) plus a span per step (retrieve / plan / verify). A span
records name, agent, task, duration and estimated tokens in/out, so a
run can be inspected the way a production trace would be — which step
was slow, which agent spent the most tokens, where a wrong answer came
from. Times are real (perf_counter); tokens are estimates (see model).
"""

import time
import uuid

from model import content_words, estimate_tokens


class Tracer:
    def __init__(self):
        self.spans = []

    def span(self, trace_id, name, agent, task_id, parent=None):
        return _Span(self, trace_id, name, agent, task_id, parent)


class _Span:
    def __init__(self, tracer, trace_id, name, agent, task_id, parent):
        self.tracer = tracer
        self.record = {
            "trace_id": trace_id,
            "span_id": uuid.uuid4().hex[:16],
            "parent_span_id": parent["span_id"] if parent else None,
            "name": name,
            "agent": agent,
            "task_id": task_id,
            "status": "ok",
        }
        self._start = time.perf_counter()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.record["duration_ms"] = round(
            (time.perf_counter() - self._start) * 1000, 3)
        if exc_type is not None:
            self.record["status"] = "error"
        self.tracer.spans.append(self.record)
        return False

    def set_tokens(self, tokens_in, tokens_out):
        self.record["tokens_in"] = tokens_in
        self.record["tokens_out"] = tokens_out


def split_parts(question):
    """Split a two-part question on ', and' / ' and ' (max 2 parts)."""
    for sep in (", and ", " and "):
        if sep in question:
            head, tail = question.split(sep, 1)
            return [head.strip(), tail.strip()]
    return [question.strip()]


class AgentResult:
    def __init__(self, agent, answer, cited):
        self.agent = agent
        self.answer = answer
        self.cited = cited  # list of fact ids the answer rests on


class DirectAgent:
    """Answer from the single best fact by naive retrieval. No plan,
    no verification: the baseline every fancier agent must beat."""

    name = "direct"

    def __init__(self, model):
        self.model = model

    def run(self, question, tracer, trace_id=None, parent=None):
        trace_id = trace_id or uuid.uuid4().hex
        with tracer.span(trace_id, "agent.run", self.name, question,
                         parent=parent) as root:
            with tracer.span(trace_id, "retrieve", self.name, question,
                             parent=root.record) as span:
                fact, _ = self.model.store.naive_retrieve(question)
                span.set_tokens(estimate_tokens(question),
                                estimate_tokens(fact["text"]))
            return AgentResult(self.name, self.model.answer_from(fact),
                               [fact["id"]])


class PlannerAgent:
    """Plan-then-answer: split the question into parts, retrieve per
    part with content-word scoring, and carry the previous part's
    answer forward as context so 'its largest moon' resolves 'its'."""

    name = "planner"

    def __init__(self, model):
        self.model = model

    def run(self, question, tracer):
        trace_id = uuid.uuid4().hex
        with tracer.span(trace_id, "agent.run", self.name, question) as root:
            parts = split_parts(question)
            answers, cited = [], []
            context = []
            for part in parts:
                with tracer.span(trace_id, "plan.retrieve", self.name,
                                 question, parent=root.record) as span:
                    fact, _ = self.model.store.content_retrieve(
                        part, extra_words=context)
                    span.set_tokens(estimate_tokens(part),
                                    estimate_tokens(fact["text"]))
                answers.append(self.model.answer_from(fact))
                cited.append(fact["id"])
                context.append(fact["answer"])
            return AgentResult(self.name, " ".join(answers), cited)


class DebateAgent:
    """Propose-then-critique: the direct agent drafts an answer, then a
    critic re-checks every part of the question with content-word
    retrieval and replaces any part whose draft does not rest on the
    right fact. Costs roughly one extra retrieval per part."""

    name = "debate"

    def __init__(self, model):
        self.model = model
        self._proposer = DirectAgent(model)

    def run(self, question, tracer):
        trace_id = uuid.uuid4().hex
        with tracer.span(trace_id, "agent.run", self.name, question) as root:
            draft = self._proposer.run(question, tracer,
                                       trace_id=trace_id, parent=root.record)
            parts = split_parts(question)
            answers, cited = [], []
            context = []
            for part in parts:
                with tracer.span(trace_id, "critic.verify", self.name,
                                 question, parent=root.record) as span:
                    fact, _ = self.model.store.content_retrieve(
                        part, extra_words=context)
                    span.set_tokens(estimate_tokens(part),
                                    estimate_tokens(fact["text"]))
                answers.append(self.model.answer_from(fact))
                cited.append(fact["id"])
                context.append(fact["answer"])
            # The critic keeps the draft only if it already cited the
            # same facts; otherwise the verified answer replaces it.
            if set(cited) == set(draft.cited) and len(parts) == 1:
                return draft
            return AgentResult(self.name, " ".join(answers), cited)


AGENTS = {
    "direct": DirectAgent,
    "planner": PlannerAgent,
    "debate": DebateAgent,
}


def content_word_list(question):
    return content_words(question)
