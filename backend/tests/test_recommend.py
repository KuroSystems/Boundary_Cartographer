"""BE-10 acceptance tests: recommendation, in-memory policy diff, retests."""

import hashlib

import pytest

from app.contracts import ApprovalStatus, AuthBasis, PathStatus
from app.fixtures import FIXTURES_DIR, load_fixtures
from app.graph import build_graph, find_paths
from app.orchestrator import run_analysis
from app.policy import ApprovalRef, load_policy
from app.policy.diff import apply_changes, build_policy_diff
from app.policy.recommend import build_recommendation
from app.replay import replay_path
from app.retest import run_retests

POLICY_DIR = FIXTURES_DIR / "policies"


def _fixture_hashes() -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(POLICY_DIR.glob("*.yaml"))
    }


@pytest.fixture()
def fixtures():
    return load_fixtures()


@pytest.fixture()
def paths_by_id(fixtures):
    return {p.path_id: p for p in find_paths(build_graph(fixtures), fixtures)}


def _verdicts(paths_by_id, fixtures):
    """Baseline statuses: replay each candidate path with the queue approval
    available to the finance workflow."""
    from app.contracts import ApprovalStatus, AuthBasis
    from app.policy import ApprovalRef

    queue = [ApprovalRef(approval_id="ap-queue", status=ApprovalStatus.APPROVED,
                         origin=AuthBasis.HUMAN_APPROVAL)]
    out = {}
    for pid, path in paths_by_id.items():
        if path.status != PathStatus.CANDIDATE:
            out[pid] = path.status.value
            continue
        events = replay_path(path, fixtures, approvals=queue)
        out[pid] = ("blocked" if any(e.decision == "blocked" for e in events)
                    else "allowed")
    return out


def test_diff_shape_and_fixtures_untouched(paths_by_id, fixtures):
    before_hashes = _fixture_hashes()
    policy = load_policy()
    findings = [
        {"code": "R2_CROSS_PURPOSE_FLOW", "rule_id": "R2", "path_id": "P1"},
        {"code": "R3_TAINTED_ARGS", "rule_id": "R3", "path_id": "P1"},
        {"code": "R3_WRONG_PURPOSE", "rule_id": "R3", "path_id": "P1"},
    ]
    rec = build_recommendation(findings)
    diff = build_policy_diff(policy, rec["changes"], fixtures.grants)
    assert diff["before"]["policy_id"] == "demo-policy-v1"
    assert diff["after"]["policy_id"] == "demo-policy-v2-simulated"
    assert diff["simulated"] is True
    assert {c["op"] for c in diff["changes"]} <= {"revoke_grant", "add_guard",
                                                 "drop_inheritance", "modify"}
    # C1 revoked the over-grant from the after-snapshot
    after_grants = {(g["identity"], g["tool"]) for g in diff["after"]["grants"]}
    assert ("document_assistant", "finance.lookup") not in after_grants
    # no fixture file under app/fixtures/policies/ was modified
    assert _fixture_hashes() == before_hashes
    # input policy object untouched (in-memory only)
    assert policy.policy_id == "demo-policy-v1"
    assert apply_changes(policy, rec["changes"]).policy_id == "demo-policy-v2-simulated"


def test_before_and_after_statuses(paths_by_id, fixtures):
    baseline = _verdicts(paths_by_id, fixtures)
    assert baseline["P1"] == "blocked" and baseline["P2"] == "blocked"
    assert baseline["P3"] == "allowed" and baseline["P5"] == "allowed"

    policy = load_policy()
    findings = [
        {"code": "R2_CROSS_PURPOSE_FLOW", "rule_id": "R2", "path_id": "P1"},
        {"code": "R3_TAINTED_ARGS", "rule_id": "R3", "path_id": "P1"},
        {"code": "R3_WRONG_PURPOSE", "rule_id": "R3", "path_id": "P1"},
    ]
    rec = build_recommendation(findings)
    queue = [ApprovalRef(approval_id="ap-queue", status=ApprovalStatus.APPROVED,
                         origin=AuthBasis.HUMAN_APPROVAL)]
    retests = run_retests(paths_by_id, fixtures, policy, rec["changes"], approvals=queue)
    by_id = {r["retest_id"]: r for r in retests}
    # after the fix: P1/P2 still blocked, P3 allowed (required), P5 allowed
    assert by_id["RT-1"]["actual"] == "blocked" and by_id["RT-1"]["passed"] is True
    assert by_id["RT-2"]["actual"] == "allowed" and by_id["RT-2"]["passed"] is True
    assert by_id["RT-3"]["actual"] == "allowed" and by_id["RT-3"]["passed"] is True


def test_c1_alone_still_leaves_p1_blocked_but_is_recorded(paths_by_id, fixtures):
    """Honest overlap: revoking the over-grant (C1) alone does not unblock P1 —
    the load-bearing controls are the R2 purpose isolation and R3 taint guard."""
    policy = load_policy()
    c1_only = [{"change_id": "C1", "op": "revoke_grant",
                "target": "document_assistant:finance.lookup", "rule_refs": ["R2"]}]
    queue = [ApprovalRef(approval_id="ap-queue", status=ApprovalStatus.APPROVED,
                         origin=AuthBasis.HUMAN_APPROVAL)]
    retests = run_retests(paths_by_id, fixtures, policy, c1_only, approvals=queue)
    rt1 = next(r for r in retests if r["retest_id"] == "RT-1")
    assert rt1["actual"] == "blocked" and rt1["passed"] is True  # still blocked
    # and the diff records the revoked grant
    diff = build_policy_diff(policy, c1_only, fixtures.grants)
    after_grants = {(g["identity"], g["tool"]) for g in diff["after"]["grants"]}
    assert ("document_assistant", "finance.lookup") not in after_grants


def test_recommendation_generated_from_findings_no_free_text_required():
    rec = build_recommendation([
        {"code": "R2_CROSS_PURPOSE_FLOW", "rule_id": "R2", "path_id": "P1"},
    ])
    assert [c["change_id"] for c in rec["changes"]] == ["C1"]  # only the backed change
    rec_all = build_recommendation([
        {"code": "R2_CROSS_PURPOSE_FLOW", "rule_id": "R2", "path_id": "P1"},
        {"code": "R3_TAINTED_ARGS", "rule_id": "R3", "path_id": "P1"},
        {"code": "R1_INSTRUCTION_NOT_AUTHORIZATION", "rule_id": "R1", "path_id": "P1"},
    ])
    # deterministic order C1, C2, C3; every change maps to rule IDs and findings
    assert [c["change_id"] for c in rec_all["changes"]] == ["C1", "C2", "C3"]
    for change in rec_all["changes"]:
        assert change["rule_refs"] and change["op"] and change["target"]
    assert rec_all["expected_effect"] == {"P1": "blocked", "P2": "blocked",
                                         "P3": "allowed", "P5": "allowed"}


def test_run_analysis_end_to_end_includes_recommendation_diff_retests():
    run = run_analysis("demo-v1")
    assert run.policy_diff.before.policy_id == "demo-policy-v1"
    assert run.policy_diff.after.policy_id == "demo-policy-v2-simulated"
    assert run.policy_diff.simulated is True
    assert [c.change_id for c in run.recommendation.changes] == ["C1", "C2", "C3"]
    by_id = {t.retest_id: t for t in run.retests}
    assert by_id["RT-2"].passed is True and by_id["RT-2"].actual == PathStatus.ALLOWED
    assert by_id["RT-3"].passed is True
    assert by_id["RT-1"].passed is True and by_id["RT-1"].actual == PathStatus.BLOCKED
    assert run.approval.status == "pending"
    assert run.approval.items[0].applied is False
    statuses = {p.path_id: p.status for p in run.paths}
    assert statuses == {"P1": PathStatus.BLOCKED, "P2": PathStatus.BLOCKED,
                        "P3": PathStatus.ALLOWED, "P4": PathStatus.DISPROVED,
                        "P5": PathStatus.ALLOWED}
