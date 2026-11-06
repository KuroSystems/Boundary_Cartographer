"""API tests for POST /runs/{run_id}/approval (BE-12).

The approval queue records decisions only: the endpoint must never call a
tool, never change the policy, and never set applied=true.
"""

import sqlite3

import app.tools.local_server as local_server
from app.policy import load_policy, policy_hash
from tests.conftest import db_path


def _approve(client, run_id, decision="approve", approval_id="ap-1", **extra):
    return client.post(
        f"/api/v1/runs/{run_id}/approval",
        json={"approval_id": approval_id, "decision": decision, **extra},
    )


def test_approve_returns_200_records_only(client, run_factory):
    _, run_id = run_factory()
    resp = _approve(client, run_id, decided_by="demo-reviewer", note="narrowing looks correct")
    assert resp.status_code == 200
    state = resp.json()
    assert state["status"] == "approved"
    item = state["items"][0]
    assert item["approval_id"] == "ap-1"
    assert item["status"] == "approved"
    assert item["decided_by"] == "demo-reviewer"
    assert item["applied"] is False
    assert item["simulated"] is True

    row = sqlite3.connect(db_path()).execute(
        "SELECT status, applied, simulated FROM approvals WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert row == ("approved", 0, 1)


def test_repeat_decision_409_and_changes_nothing(client, run_factory):
    _, run_id = run_factory()
    first = _approve(client, run_id, decided_by="demo-reviewer")
    assert first.status_code == 200
    again = _approve(client, run_id, decision="reject", decided_by="someone-else")
    assert again.status_code == 409
    err = again.json()["error"]
    assert err["code"] == "APPROVAL_ALREADY_DECIDED"
    assert err["details"] == {"approval_id": "ap-1", "status": "approved"}
    # the recorded decision is unchanged by the repeat attempt
    row = sqlite3.connect(db_path()).execute(
        "SELECT status, decided_by FROM approvals WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert row == ("approved", "demo-reviewer")


def test_invalid_decision_value_422_validation_error(client, run_factory):
    _, run_id = run_factory()
    resp = _approve(client, run_id, decision="maybe")
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    # nothing was recorded
    row = sqlite3.connect(db_path()).execute(
        "SELECT status FROM approvals WHERE run_id = ?", (run_id,)
    ).fetchone()
    assert row[0] == "pending"


def test_approval_unknown_run_404_run_not_found(client):
    resp = _approve(client, "NOPE")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RUN_NOT_FOUND"


def test_approval_unknown_item_404(client, run_factory):
    _, run_id = run_factory()
    resp = _approve(client, run_id, approval_id="ap-99")
    assert resp.status_code == 404


def test_approval_performs_no_tool_call_and_no_policy_change(client, run_factory, monkeypatch):
    resp, run_id = run_factory()
    run_before = client.get(f"/api/v1/runs/{run_id}").json()
    policy_before = load_policy()
    hash_before = policy_hash(policy_before)
    rules_before = [dict(r) for r in policy_before.rules]

    calls = []
    real_call = local_server.call

    def spy(req, fixtures=None):
        calls.append(req)
        return real_call(req, fixtures)

    monkeypatch.setattr(local_server, "call", spy)
    resp = _approve(client, run_id, decided_by="demo-reviewer")
    assert resp.status_code == 200
    assert calls == [], "approval endpoint must not call any tool"

    policy_after = load_policy()
    assert policy_hash(policy_after) == hash_before
    assert [dict(r) for r in policy_after.rules] == rules_before
    # no grant changed either: the run's policy snapshot is untouched
    assert run_after_policy_snapshot(client, run_id) == run_before["policy_diff"]["before"]
    run_after = client.get(f"/api/v1/runs/{run_id}").json()
    assert run_after["input_digest"] == run_before["input_digest"]


def run_after_policy_snapshot(client, run_id):
    return client.get(f"/api/v1/runs/{run_id}").json()["policy_diff"]["before"]
