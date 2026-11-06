"""BE-09 acceptance tests: LangGraph orchestration with five fixed roles."""

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts import PathStatus, RunResponse
from app.orchestrator import build_orchestrator_graph, run_analysis
from app.orchestrator import roles as roles_mod
from app.orchestrator.messages import (
    EvidenceReport,
    InventoryReport,
    PathFindReport,
    ReplayReport,
    VerifyReport,
)

ORCH_PKG = Path(__file__).resolve().parents[1] / "app" / "orchestrator"
BANNED_IMPORTS = {"openai", "anthropic", "httpx", "requests", "socket", "urllib"}


def test_graph_compiles():
    app = build_orchestrator_graph()
    assert app is not None


def test_each_role_emits_its_typed_message():
    state = {"scenario_id": "demo-v1", "retry_count": 0}
    state.update(roles_mod.inventory_node(state))
    assert InventoryReport.model_validate(state["inventory"])
    state.update(roles_mod.path_finder_node(state))
    report = PathFindReport.model_validate(state["path_find"])
    assert report.paths
    state.update(roles_mod.injection_tester_node(state))
    assert ReplayReport.model_validate(state["replay"]).replay_events
    state.update(roles_mod.policy_verifier_node(state))
    assert VerifyReport.model_validate(state["verify"]).paths
    state.update(roles_mod.evidence_writer_node(state))
    run = EvidenceReport.model_validate(state["evidence"]).run
    assert RunResponse.model_validate(run)


def test_exactly_five_roles_each_invoked_once_per_run(monkeypatch):
    calls = {name: 0 for name in roles_mod.ROLE_NAMES}
    assert len(roles_mod.ROLE_NAMES) == 5

    def wrap(name, fn):
        def inner(state):
            calls[name] += 1
            return fn(state)
        return inner

    monkeypatch.setattr(
        roles_mod, "inventory_node", wrap("inventory", roles_mod.inventory_node)
    )
    monkeypatch.setattr(
        roles_mod, "path_finder_node", wrap("path_finder", roles_mod.path_finder_node)
    )
    monkeypatch.setattr(roles_mod, "injection_tester_node",
                        wrap("injection_tester", roles_mod.injection_tester_node))
    monkeypatch.setattr(roles_mod, "policy_verifier_node",
                        wrap("policy_verifier", roles_mod.policy_verifier_node))
    monkeypatch.setattr(roles_mod, "evidence_writer_node",
                        wrap("evidence_writer", roles_mod.evidence_writer_node))

    # rebuild the graph so it picks up the wrapped nodes
    from app.orchestrator import graph as graph_mod
    monkeypatch.setattr(graph_mod, "inventory_node", roles_mod.inventory_node)
    monkeypatch.setattr(graph_mod, "path_finder_node", roles_mod.path_finder_node)
    monkeypatch.setattr(graph_mod, "injection_tester_node", roles_mod.injection_tester_node)
    monkeypatch.setattr(graph_mod, "policy_verifier_node", roles_mod.policy_verifier_node)
    monkeypatch.setattr(graph_mod, "evidence_writer_node", roles_mod.evidence_writer_node)
    app = build_orchestrator_graph()
    app.invoke({"scenario_id": "demo-v1", "retry_count": 0})
    assert all(c == 1 for c in calls.values()), calls


def test_orchestrator_package_has_no_llm_or_network_imports():
    for path in sorted(ORCH_PKG.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in BANNED_IMPORTS
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in BANNED_IMPORTS


def test_malformed_message_raises_validation_error():
    with pytest.raises(ValidationError):
        PathFindReport.model_validate({"not_paths": []})  # missing required `paths`


def test_run_analysis_returns_valid_run_response_and_is_deterministic():
    r1 = run_analysis("demo-v1")
    r2 = run_analysis("demo-v1")
    assert isinstance(r1, RunResponse)
    assert r1.scenario_id == "demo-v1"
    assert r1.status == "completed"
    d1 = r1.model_dump(by_alias=True, mode="json")
    d2 = r2.model_dump(by_alias=True, mode="json")
    for key in ("run_id", "generated_at"):
        d1.pop(key)
        d2.pop(key)
    # evidence records embed run identity/timestamp (and hashes derived from
    # them) by contract — normalize before comparing
    for d in (d1, d2):
        for rec in d["evidence"]:
            rec["run_id"] = "<run>"
            rec["captured_at"] = "<ts>"
            rec["hash"] = "<hash>"
            rec["prev_hash"] = "<prev>" if rec["prev_hash"] else rec["prev_hash"]
    assert d1 == d2
    # paths got final verifier statuses
    statuses = {p.path_id: p.status for p in r1.paths}
    assert statuses["P1"] == PathStatus.BLOCKED
    assert statuses["P4"] == PathStatus.DISPROVED
    assert statuses["P3"] == PathStatus.ALLOWED


def test_orchestration_trace_in_evidence_without_wallclock_variability():
    run = run_analysis("demo-v1")
    orch = [e for e in run.evidence if e.summary.startswith("orchestrator role=")]
    assert len(orch) == 5
    roles_seen = [e.summary.split("role=")[1].split(" ")[0] for e in orch]
    assert roles_seen == ["inventory", "path_finder", "injection_tester",
                          "policy_verifier", "evidence_writer"]
    # hash chain intact
    assert run.evidence[0].prev_hash is None
    for prev, cur in zip(run.evidence, run.evidence[1:]):
        assert cur.prev_hash == prev.hash
