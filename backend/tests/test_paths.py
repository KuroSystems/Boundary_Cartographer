"""BE-06 acceptance tests: candidate path search with candidate/disproved labelling."""

from pathlib import Path

import pytest

from app.contracts import Basis, PathStatus
from app.fixtures import load_fixtures
from app.graph import build_graph, find_paths, search_candidates

PATHS_SOURCE = (Path(__file__).resolve().parents[1] / "app" / "graph" / "paths.py").read_text()


@pytest.fixture()
def fixtures():
    return load_fixtures()


@pytest.fixture()
def graph(fixtures):
    return build_graph(fixtures)


def test_at_least_two_candidates_terminate_at_finance_export(graph, fixtures):
    paths = find_paths(graph, fixtures)
    export_candidates = [
        p for p in paths
        if p.sink == "tool:finance.export" and p.status == PathStatus.CANDIDATE
    ]
    assert len(export_candidates) >= 2
    for p in export_candidates:
        assert p.status == PathStatus.CANDIDATE  # never blocked/allowed here
        assert p.basis == Basis.GRAPH_REACHABILITY
        assert p.reasons == []
        assert p.history[0].status == PathStatus.CANDIDATE
        assert p.history[0].at_step == "path_finder"


def test_p4_is_disproved_with_structural_reason_not_candidate_not_blocked(graph, fixtures):
    paths = {p.path_id: p for p in find_paths(graph, fixtures)}
    p4 = paths["P4"]
    assert p4.status == PathStatus.DISPROVED
    assert p4.status != PathStatus.CANDIDATE
    assert p4.status != PathStatus.BLOCKED
    assert len(p4.reasons) == 1
    assert p4.reasons[0].code == "R3_WRONG_IDENTITY"
    assert p4.reasons[0].rule_id == "R3"
    assert "no may_invoke edge" in p4.reasons[0].message
    assert p4.reasons[0].evidence_ids == ["src:grant-matrix"]


def test_golden_five_paths_present(graph, fixtures):
    assert [p.path_id for p in find_paths(graph, fixtures)] == ["P1", "P2", "P3", "P4", "P5"]


def test_determinism_identical_order_and_ids(graph, fixtures):
    r1 = [p.model_dump(mode="json") for p in find_paths(graph, fixtures)]
    fx2 = load_fixtures()
    r2 = [p.model_dump(mode="json") for p in find_paths(build_graph(fx2), fx2)]
    assert r1 == r2
    args = (graph, "source:doc-untrusted-001", ["tool:finance.export"])
    s1 = [p.model_dump(mode="json") for p in search_candidates(*args)]
    s2 = [p.model_dump(mode="json") for p in search_candidates(*args)]
    assert s1 == s2


def test_negative_removing_delegates_to_edge_removes_p1_p2(graph, fixtures):
    g2 = graph.copy()
    g2.remove_edge("identity:document_assistant", "identity:finance_analyst")
    paths = find_paths(g2, fixtures)
    ids = [p.path_id for p in paths]
    assert "P1" not in ids and "P2" not in ids
    # and the code never falls back to a "confirmed"/allowed/blocked label
    for p in paths:
        assert p.status in (PathStatus.CANDIDATE, PathStatus.DISPROVED)


def test_path_search_does_not_import_policy_engine():
    assert "app.policy" not in PATHS_SOURCE
    assert "from app import policy" not in PATHS_SOURCE
    assert "import policy" not in PATHS_SOURCE
