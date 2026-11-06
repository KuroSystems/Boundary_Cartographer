"""BE-03 acceptance tests: SQLite schema + append-only repository (in-memory DB)."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from app.store import (
    ApprovalConflict,
    append_evidence,
    compute_hash,
    create_approval_item,
    decide_approval,
    get_approval_state,
    get_run,
    insert_run,
    list_evidence,
    open_db,
)

REPO_SOURCE = (Path(__file__).resolve().parents[1] / "app" / "store" / "repository.py").read_text()


@pytest.fixture()
def conn():
    c = open_db(":memory:")
    yield c
    c.close()


def _run(run_id: str = "run-1") -> dict:
    return {
        "run_id": run_id,
        "scenario_id": "demo-v1",
        "status": "completed",
        "input_digest": "sha256:" + "b" * 64,
        "generated_at": "2026-11-06T10:00:00Z",
        "summary": {"headline": "h"},
    }


def _record(evidence_id: str, run_id: str = "run-1") -> dict:
    return {
        "evidence_id": evidence_id,
        "kind": "source",
        "run_id": run_id,
        "captured_at": "2026-11-06T10:00:00Z",
        "source_id": "src:doc-untrusted-001",
        "summary": f"record {evidence_id}",
        "trace": {"path_ids": ["P1"], "event_ids": []},
    }


def test_run_round_trip_identical(conn):
    run = _run()
    insert_run(conn, run)
    assert get_run(conn, "run-1") == run
    assert get_run(conn, "missing") is None


def test_evidence_hash_chain_three_records(conn):
    insert_run(conn, _run())
    r1 = append_evidence(conn, "run-1", _record("src:doc-untrusted-001"))
    r2 = append_evidence(conn, "run-1", _record("src:manifest"))
    r3 = append_evidence(conn, "run-1", _record("src:grant-matrix"))

    assert r1["prev_hash"] is None
    assert r2["prev_hash"] == r1["hash"]
    assert r3["prev_hash"] == r2["hash"]

    # hash = sha256(prev_hash + canonical_json(record-without-hash))
    for prev, rec in [(None, r1), (r1["hash"], r2), (r2["hash"], r3)]:
        expected = compute_hash(prev, rec)
        assert rec["hash"] == expected
        body = {k: v for k, v in rec.items() if k != "hash"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        manual = "sha256:" + hashlib.sha256(((prev or "") + canonical).encode()).hexdigest()
        assert rec["hash"] == manual

    listed = list_evidence(conn, "run-1")
    assert [r["evidence_id"] for r in listed] == [
        "src:doc-untrusted-001", "src:manifest", "src:grant-matrix",
    ]


def test_evidence_update_and_delete_forbidden(conn):
    insert_run(conn, _run())
    append_evidence(conn, "run-1", _record("src:doc-untrusted-001"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE evidence SET summary = 'x' WHERE run_id = 'run-1'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM evidence WHERE run_id = 'run-1'")
    conn.rollback()
    # chain intact after the forbidden attempts
    assert len(list_evidence(conn, "run-1")) == 1


def test_decide_approval_single_shot_and_conflict(conn):
    insert_run(conn, _run())
    create_approval_item(conn, "run-1", {
        "approval_id": "ap-1",
        "subject": {"type": "recommendation", "id": "REC-1"},
        "requested_at": "2026-11-06T10:00:00Z",
        "effect": "records a decision only; no policy or tool action is performed",
    })

    decided = decide_approval(conn, "run-1", "ap-1", "approve", decided_by="reviewer", note="ok")
    assert decided["status"] == "approved"
    assert decided["decided_by"] == "reviewer"
    assert decided["applied"] is False
    assert decided["simulated"] is True

    with pytest.raises(ApprovalConflict):
        decide_approval(conn, "run-1", "ap-1", "reject", decided_by="other")

    # second call changed nothing
    state = get_approval_state(conn, "run-1")
    assert state["status"] == "approved"
    assert state["items"][0]["status"] == "approved"
    assert state["items"][0]["decided_by"] == "reviewer"
    assert state["items"][0]["note"] == "ok"


def test_approval_defaults_and_never_applied(conn):
    insert_run(conn, _run())
    item = create_approval_item(conn, "run-1", {
        "approval_id": "ap-1",
        "subject": {"type": "recommendation", "id": "REC-1"},
    })
    assert item["applied"] is False and item["simulated"] is True
    assert item["status"] == "pending"
    decide_approval(conn, "run-1", "ap-1", "reject")
    item = get_approval_state(conn, "run-1")["items"][0]
    assert item["applied"] is False  # deciding never applies anything
    # no code path writes applied = 1 (inspect code with docstrings stripped)
    import ast

    tree = ast.parse(REPO_SOURCE)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
            ):
                node.body = node.body[1:]
    code = ast.unparse(tree)
    assert "applied = 1" not in code
    assert "applied=1" not in code
    assert "applied', 1" not in code
    assert 'applied", 1' not in code


def test_schema_version_recorded(conn):
    row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    assert row["v"] == 1


def test_foreign_keys_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        append_evidence(conn, "no-such-run", _record("x", run_id="no-such-run"))
