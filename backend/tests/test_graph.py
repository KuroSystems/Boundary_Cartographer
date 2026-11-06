"""BE-05 acceptance tests: deterministic NetworkX graph construction + serialization."""

import pytest

from app.contracts import EdgeKind, Graph, NodeKind
from app.fixtures import load_fixtures
from app.graph import build_graph, serialize_graph, serialize_graph_json

KNOWN_SOURCES = {
    "src:manifest",
    "src:grant-matrix",
    "src:policy-rule-1",
    "src:policy-rule-2",
    "src:policy-rule-3",
    "src:doc-untrusted-001",  # the seeded document is itself a registered source
}

EXPECTED_NODE_IDS = {
    "source:doc-untrusted-001",
    "identity:document_assistant",
    "identity:finance_analyst",
    "tool:document.read",
    "tool:document.summarize",
    "tool:finance.lookup",
    "tool:finance.export",
    "data_scope:docs:read_untrusted",
    "data_scope:docs:summarize",
    "data_scope:finance:lookup_public",
    "data_scope:finance:lookup",
    "data_scope:finance:export",
    "output:summary",
    "output:export_report",
}


@pytest.fixture()
def fixtures():
    return load_fixtures()


@pytest.fixture()
def graph(fixtures):
    return serialize_graph(build_graph(fixtures))


def test_golden_snapshot_node_ids_and_counts(graph: Graph):
    ids = {n.id for n in graph.nodes}
    assert ids == EXPECTED_NODE_IDS
    assert len(graph.nodes) >= 14
    assert len(graph.edges) >= 20
    # stable IDs
    assert "tool:finance.export" in ids
    assert any(e.id == "edge:05" for e in graph.edges)


def test_every_edge_traceable_to_a_known_source(graph: Graph):
    for edge in graph.edges:
        assert edge.source_ids, f"{edge.id} has no source_ids"
        assert set(edge.source_ids) <= KNOWN_SOURCES, f"{edge.id}: {edge.source_ids}"


def test_may_invoke_edges_come_from_grant_matrix(fixtures, graph: Graph):
    grants = {(f"identity:{g['identity']}", f"tool:{g['tool']}") for g in fixtures.grants}
    may_invoke = {(e.from_, e.to) for e in graph.edges if e.kind == EdgeKind.MAY_INVOKE}
    assert may_invoke == grants
    for edge in graph.edges:
        if edge.kind == EdgeKind.MAY_INVOKE:
            assert edge.purposes and edge.scopes
            assert edge.source_ids == ["src:grant-matrix"]


def test_no_may_invoke_document_assistant_to_finance_export(graph: Graph):
    # powers the `disproved` P4 case
    bad = [
        e for e in graph.edges
        if e.kind == EdgeKind.MAY_INVOKE
        and e.from_ == "identity:document_assistant"
        and e.to == "tool:finance.export"
    ]
    assert bad == []


def test_finance_export_is_critical_sensitive_sink(fixtures, graph: Graph):
    node = next(n for n in graph.nodes if n.id == "tool:finance.export")
    assert node.kind == NodeKind.TOOL
    assert node.risk == "critical"
    assert "tool:finance.export" in fixtures.sensitive_sinks


def test_build_is_pure_identical_serialized_json(fixtures):
    j1 = serialize_graph_json(build_graph(fixtures))
    j2 = serialize_graph_json(build_graph(load_fixtures()))
    assert j1 == j2
    # and it validates as the contract Graph
    Graph.model_validate(j1)


def test_edge_kinds_cover_the_contract_set(graph: Graph):
    kinds = {e.kind for e in graph.edges}
    assert {EdgeKind.FLOWS_TO, EdgeKind.MAY_INVOKE, EdgeKind.READS,
            EdgeKind.PRODUCES, EdgeKind.DERIVED_FROM, EdgeKind.DELEGATES_TO} <= kinds
