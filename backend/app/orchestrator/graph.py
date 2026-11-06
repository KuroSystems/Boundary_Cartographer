"""LangGraph StateGraph wiring (BE-09): Inventory → PathFinder → InjectionTester
→ PolicyVerifier → EvidenceWriter, linear plus one conditional retry edge
bounded to 1 (path_finder may run at most twice when no candidate paths exist).
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.orchestrator.roles import (
    evidence_writer_node,
    injection_tester_node,
    inventory_node,
    path_finder_node,
    policy_verifier_node,
)

MAX_RETRIES = 1


class OrchState(TypedDict, total=False):
    scenario_id: str
    inventory: dict
    path_find: dict
    graph: dict
    replay: dict
    verify: dict
    evidence: dict
    retry_count: int


def _needs_retry(state: OrchState) -> str:
    """Conditional edge: retry path_finder once if it found zero paths."""
    paths = state.get("path_find", {}).get("paths", [])
    if not paths and state.get("retry_count", 0) < MAX_RETRIES:
        return "retry"
    return "continue"


def _retry_bump_node(state: OrchState) -> dict:
    return {"retry_count": state.get("retry_count", 0) + 1}


def build_orchestrator_graph():
    """Compile the orchestrator StateGraph."""
    g = StateGraph(OrchState)
    g.add_node("inventory", inventory_node)
    g.add_node("path_finder", path_finder_node)
    g.add_node("retry_bump", _retry_bump_node)
    g.add_node("injection_tester", injection_tester_node)
    g.add_node("policy_verifier", policy_verifier_node)
    g.add_node("evidence_writer", evidence_writer_node)

    g.add_edge(START, "inventory")
    g.add_edge("inventory", "path_finder")
    g.add_conditional_edges(
        "path_finder",
        _needs_retry,
        {"retry": "retry_bump", "continue": "injection_tester"},
    )
    g.add_edge("retry_bump", "path_finder")  # bounded: retry_count reaches MAX_RETRIES
    g.add_edge("injection_tester", "policy_verifier")
    g.add_edge("policy_verifier", "evidence_writer")
    g.add_edge("evidence_writer", END)
    return g.compile()
