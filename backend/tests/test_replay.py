"""BE-08 acceptance tests: safe offline injection replay engine."""

import pytest

from app.contracts import ApprovalStatus, AuthBasis, Decision, ReplayEvent
from app.fixtures import load_fixtures
from app.graph import build_graph, find_paths
from app.policy import ApprovalRef
from app.replay import detect_untrusted_claims, replay_path
from app.replay import engine as replay_engine
from app.tools import local_server

KNOWN_SOURCES = {
    "src:manifest", "src:grant-matrix",
    "src:policy-rule-1", "src:policy-rule-2", "src:policy-rule-3",
    "src:doc-untrusted-001",
}


@pytest.fixture()
def fixtures():
    return load_fixtures()


@pytest.fixture()
def p1(fixtures):
    paths = {p.path_id: p for p in find_paths(build_graph(fixtures), fixtures)}
    return paths["P1"]


@pytest.fixture()
def p5(fixtures):
    paths = {p.path_id: p for p in find_paths(build_graph(fixtures), fixtures)}
    return paths["P5"]


def test_p1_replay_six_events_ending_blocked_export(p1, fixtures):
    events = replay_path(p1, fixtures)
    assert len(events) == 6
    last = events[-1]
    assert last.tool == "finance.export"
    assert last.decision == Decision.BLOCKED
    assert last.executed is False
    assert last.tool_result is None
    assert {"R2", "R3"} <= set(last.policy.rule_ids)


def test_forged_approval_reported_not_accepted(p1, fixtures):
    events = replay_path(p1, fixtures)
    export = events[-1]
    codes = [r.code for r in export.policy.reasons]
    # forged approval surfaced as untrusted-origin (R1) and invalid (R3) — never accepted
    assert "R3_NO_VALID_APPROVAL" in codes
    assert "R1_INSTRUCTION_NOT_AUTHORIZATION" in codes
    reason = next(r for r in export.policy.reasons if r.code == "R3_NO_VALID_APPROVAL")
    assert "origin=untrusted_content" in reason.message
    assert export.decision == Decision.BLOCKED


def test_claims_detected_as_text_tokens_only(fixtures):
    claims = detect_untrusted_claims(fixtures.document["content"])
    kinds = {c["kind"] for c in claims}
    assert "approval_claim" in kinds and "identity_claim" in kinds
    assert any(c["ref"] == "CFO-2026-11" for c in claims)
    assert any(c["ref"] == "finance_analyst" for c in claims)


def test_tool_spy_only_allowed_mock_tools_invoked(p1, fixtures, monkeypatch):
    invoked = []
    real_call = local_server.call

    def spy(req, fixtures_arg=None):
        invoked.append(req.tool)
        return real_call(req, fixtures_arg)

    monkeypatch.setattr(replay_engine.local_server, "call", spy)
    events = replay_path(p1, fixtures)
    assert set(invoked) <= {"document.read", "document.summarize"}
    assert "finance.export" not in invoked
    assert "finance.lookup" not in invoked
    assert all(e.executed is False for e in events if e.decision != Decision.ALLOWED)


def test_unblocked_variant_p5_lookup_executed_export_never(p5, fixtures, monkeypatch):
    invoked = []
    real_call = local_server.call

    def spy(req, fixtures_arg=None):
        invoked.append(req.tool)
        return real_call(req, fixtures_arg)

    monkeypatch.setattr(replay_engine.local_server, "call", spy)
    queue = [ApprovalRef(approval_id="ap-1", status=ApprovalStatus.APPROVED,
                         origin=AuthBasis.HUMAN_APPROVAL)]
    events = replay_path(p5, fixtures, approvals=queue)
    lookup = next(e for e in events if e.tool == "finance.lookup")
    export = next(e for e in events if e.tool == "finance.export")
    assert lookup.decision == Decision.ALLOWED and lookup.executed is True
    assert export.decision == Decision.ALLOWED and export.executed is False
    assert export.tool_result is None
    assert invoked == ["finance.lookup"]  # finance.export never invoked


def test_events_have_resolvable_source_ids_and_no_instruction_field(p1, fixtures):
    events = replay_path(p1, fixtures)
    for e in events:
        assert isinstance(e, ReplayEvent)  # schema-valid by construction
        assert e.source_ids and set(e.source_ids) <= KNOWN_SOURCES
        dumped = e.model_dump(mode="json")
        assert "instruction" not in dumped
        assert "instruction" not in dumped["policy"]


def test_document_text_never_in_preview_or_decision(p1, fixtures):
    events = replay_path(p1, fixtures)
    banned = ["SYSTEM NOTICE", "full_ledger", "ignore previous instructions", "CFO-2026-11"]
    for e in events:
        for fragment in banned:
            assert fragment not in e.input_preview
            assert fragment not in e.decision
            assert fragment not in e.policy.model_dump_json()


def test_sanitization_disabled_engine_still_refuses_text_as_authorization(
        p1, fixtures, monkeypatch):
    # Defense in depth: even if claim detection is disabled, the evaluator
    # never treats document text as authorization.
    monkeypatch.setattr(replay_engine, "detect_untrusted_claims", lambda text: [])
    events = replay_path(p1, fixtures)
    export = events[-1]
    assert export.decision == Decision.BLOCKED
    assert export.executed is False
    assert "R3_NO_VALID_APPROVAL" in [r.code for r in export.policy.reasons]
