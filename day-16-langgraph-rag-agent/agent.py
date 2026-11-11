"""LangGraph agent: RAG tool + human-approval gate + observability trace.

Graph (StateGraph, MemorySaver checkpointer):

    START -> retrieve -> route
      route: top score >= threshold -> approval_gate
             top score <  threshold -> refuse
    approval_gate -> approved? -> answer
                   -> not approved -> refuse
    answer / refuse -> END

* ``retrieve`` calls the TF-IDF retriever (``retrieval.py``) as the agent's
  tool — the same RAG half built on Day 10, now wired into an agent.
* ``approval_gate`` is a real LangGraph human-in-the-loop step: it calls
  ``interrupt()`` and pauses until a human resumes with ``Command(resume=...)``.
  Pass ``auto_approve=True`` (CLI ``--auto-approve``, used by the eval and the
  tests) to skip the pause. Refusing at the gate ends in ``refuse``.
* ``answer`` is a local deterministic stand-in for an LLM call: it composes
  the answer from the top retrieved passage and cites it. No model API, no
  paid calls, no API key needed. Swapping in a real chat model means replacing
  this one node — the graph, tool, gate and traces stay the same.
* Every node appends to ``trace`` (list of node names visited); ``run.py``
  writes one JSONL line per run to ``traces.jsonl`` — the observability half.

State keys: question, retrieved, top_score, approved, answer, decision,
trace, auto_approve.
"""

import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command, interrupt

from retrieval import Retriever

RETRIEVAL_THRESHOLD = 0.15


class AgentState(TypedDict):
    question: str
    retrieved: list
    top_score: float
    approved: bool | None
    answer: str
    decision: str
    trace: Annotated[list, operator.add]
    auto_approve: bool


def _retriever():
    return Retriever.from_file()


def retrieve_node(state: AgentState) -> dict:
    results = _retriever().retrieve(state["question"], top_k=3)
    top = results[0]["score"] if results else 0.0
    return {
        "retrieved": results,
        "top_score": top,
        "trace": ["retrieve"],
    }


def route_after_retrieve(state: AgentState) -> str:
    if state["top_score"] < RETRIEVAL_THRESHOLD:
        return "refuse"
    return "approval_gate"


def approval_gate_node(state: AgentState) -> dict:
    if state.get("auto_approve"):
        return {"approved": True, "trace": ["approval_gate:auto-approved"]}
    top = state["retrieved"][0]
    decision = interrupt(
        {
            "question": state["question"],
            "draft_answer": top["text"],
            "source": f"{top['title']} (score={top['score']:.3f})",
            "prompt": "Approve this retrieved answer? Reply True to approve, False to refuse.",
        }
    )
    return {"approved": bool(decision), "trace": ["approval_gate:human-decision"]}


def route_after_gate(state: AgentState) -> str:
    return "answer" if state.get("approved") else "refuse"


def answer_node(state: AgentState) -> dict:
    top = state["retrieved"][0]
    answer = (
        f"{top['text']} [source: {top['title']}, "
        f"retrieval score={top['score']:.3f}]"
    )
    return {"answer": answer, "decision": "answered", "trace": ["answer"]}


def refuse_node(state: AgentState) -> dict:
    if state.get("approved") is False:
        reason = "Not approved at the human gate."
    else:
        reason = "Not found in the provided documents."
    return {
        "answer": reason,
        "decision": "refused",
        "trace": ["refuse"],
    }


def build_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("answer", answer_node)
    graph.add_node("refuse", refuse_node)
    graph.set_entry_point("retrieve")
    graph.add_conditional_edges("retrieve", route_after_retrieve)
    graph.add_conditional_edges("approval_gate", route_after_gate)
    graph.add_edge("answer", END)
    graph.add_edge("refuse", END)
    return graph.compile(checkpointer=checkpointer or MemorySaver())


def run_question(question, auto_approve=True, thread_id="default"):
    """Run one question through the graph.

    With auto_approve=False the graph pauses at the gate and this returns
    {"__interrupt__": ...}; resume with ``resume_question(thread_id, True/False)``.
    Returns the final state dict (or the interrupt payload).
    """
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    initial = {
        "question": question,
        "retrieved": [],
        "top_score": 0.0,
        "approved": None,
        "answer": "",
        "decision": "",
        "trace": [],
        "auto_approve": auto_approve,
    }
    result = graph.invoke(initial, config=config)
    return result, graph, config


def resume_question(graph, config, approve: bool):
    """Resume a paused run after the human gate. Returns final state."""
    return graph.invoke(Command(resume=approve), config=config)
