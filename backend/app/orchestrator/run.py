"""Synchronous run wrapper (BE-09): run_analysis(scenario_id) -> RunResponse."""

from app.contracts import RunResponse
from app.orchestrator.graph import build_orchestrator_graph


def run_analysis(scenario_id: str = "demo-v1") -> RunResponse:
    """Run the full offline analysis synchronously and return a valid RunResponse.

    Deterministic: two calls with the same scenario differ only in
    run_id / generated_at.
    """
    app = build_orchestrator_graph()
    final_state = app.invoke({"scenario_id": scenario_id, "retry_count": 0})
    return RunResponse.model_validate(final_state["evidence"]["run"])
