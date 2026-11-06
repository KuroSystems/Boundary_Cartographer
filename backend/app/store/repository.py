"""Append-only repository over SQLite (BE-03).

- insert_run / get_run: store and read back the full RunResponse payload.
- append_evidence: assigns seq (AUTOINCREMENT), prev_hash (hash of the previous
  record of the run) and hash = sha256(prev_hash + canonical_json(record)).
- create_approval_item / decide_approval (single-shot; ApprovalConflict on repeat)
  / get_approval_state.

The approval queue records decisions only: `applied` is always 0 and `simulated`
always 1 — no code path in this module ever writes applied = 1.
"""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(prev_hash: str | None, record: dict) -> str:
    """hash = sha256(prev_hash + canonical_json(record-without-hash))."""
    body = {k: v for k, v in record.items() if k != "hash"}
    material = (prev_hash or "") + _canonical(body)
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


class ApprovalConflict(Exception):
    """Raised when deciding an approval item that was already decided (→ HTTP 409)."""


# ---------------------------------------------------------------- runs
def insert_run(conn: sqlite3.Connection, run: dict) -> None:
    conn.execute(
        "INSERT INTO runs (run_id, scenario_id, status, payload, input_digest, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            run["run_id"],
            run["scenario_id"],
            run["status"],
            _canonical(run),
            run["input_digest"],
            run.get("generated_at") or _utcnow(),
        ),
    )
    conn.commit()


def get_run(conn: sqlite3.Connection, run_id: str) -> dict | None:
    raw = get_run_raw(conn, run_id)
    return json.loads(raw) if raw is not None else None


def get_run_raw(conn: sqlite3.Connection, run_id: str) -> str | None:
    """The stored payload string, exactly as persisted (canonical JSON)."""
    row = conn.execute("SELECT payload FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    return row["payload"] if row else None


# ---------------------------------------------------------------- evidence
def append_evidence(conn: sqlite3.Connection, run_id: str, record: dict) -> dict:
    """Append one evidence record, assigning prev_hash and hash (hash chain)."""
    row = conn.execute(
        "SELECT hash FROM evidence WHERE run_id = ? ORDER BY seq DESC LIMIT 1", (run_id,)
    ).fetchone()
    prev_hash = row["hash"] if row else None
    record = {**record, "prev_hash": prev_hash}
    record = {**record, "hash": compute_hash(prev_hash, record)}
    conn.execute(
        "INSERT INTO evidence (evidence_id, run_id, kind, source_id, summary, hash,"
        " prev_hash, record, captured_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            record["evidence_id"],
            run_id,
            record["kind"],
            record["source_id"],
            record["summary"],
            record["hash"],
            record["prev_hash"],
            _canonical(record),
            record["captured_at"],
        ),
    )
    conn.commit()
    return record


def list_evidence(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT record FROM evidence WHERE run_id = ? ORDER BY seq ASC", (run_id,)
    ).fetchall()
    return [json.loads(r["record"]) for r in rows]


# ---------------------------------------------------------------- approvals
def create_approval_item(conn: sqlite3.Connection, run_id: str, item: dict) -> dict:
    """Insert a pending approval item. applied=0 / simulated=1 by schema default."""
    conn.execute(
        "INSERT INTO approvals (approval_id, run_id, subject_type, subject_id, status,"
        " requested_at, effect) VALUES (?, ?, ?, ?, 'pending', ?, ?)",
        (
            item["approval_id"],
            run_id,
            item["subject"]["type"],
            item["subject"]["id"],
            item.get("requested_at") or _utcnow(),
            item.get("effect", "records a decision only; no policy or tool action is performed"),
        ),
    )
    conn.commit()
    return get_approval_state(conn, run_id)["items"][-1]


def decide_approval(
    conn: sqlite3.Connection,
    run_id: str,
    approval_id: str,
    decision: str,
    decided_by: str | None = None,
    note: str | None = None,
) -> dict:
    """Record an approve/reject decision exactly once (single-shot).

    Raises ApprovalConflict if the item was already decided; the second call
    changes nothing. Never touches `applied` (stays 0) — records a decision only.
    """
    if decision not in ("approve", "reject"):
        raise ValueError(f"invalid decision {decision!r}; must be 'approve' or 'reject'")
    status = "approved" if decision == "approve" else "rejected"
    cur = conn.execute(
        "UPDATE approvals SET status = ?, decided_by = ?, decided_at = ?, note = ?"
        " WHERE run_id = ? AND approval_id = ? AND status = 'pending'",
        (status, decided_by, _utcnow(), note, run_id, approval_id),
    )
    if cur.rowcount == 0:
        existing = conn.execute(
            "SELECT approval_id FROM approvals WHERE run_id = ? AND approval_id = ?",
            (run_id, approval_id),
        ).fetchone()
        if existing is None:
            raise KeyError(f"approval {approval_id!r} not found for run {run_id!r}")
        raise ApprovalConflict(f"approval {approval_id!r} already decided")
    conn.commit()
    row = conn.execute(
        "SELECT * FROM approvals WHERE run_id = ? AND approval_id = ?", (run_id, approval_id)
    ).fetchone()
    return _row_to_item(row)


def get_approval_state(conn: sqlite3.Connection, run_id: str) -> dict:
    rows = conn.execute(
        "SELECT * FROM approvals WHERE run_id = ? ORDER BY rowid ASC", (run_id,)
    ).fetchall()
    items = [_row_to_item(r) for r in rows]
    statuses = [i["status"] for i in items]
    overall = "pending" if "pending" in statuses else (statuses[0] if statuses else "pending")
    return {"status": overall, "items": items}


def _row_to_item(row: sqlite3.Row) -> dict:
    return {
        "approval_id": row["approval_id"],
        "subject": {"type": row["subject_type"], "id": row["subject_id"]},
        "status": row["status"],
        "requested_at": row["requested_at"],
        "decided_by": row["decided_by"],
        "decided_at": row["decided_at"],
        "note": row["note"],
        "applied": bool(row["applied"]),
        "simulated": bool(row["simulated"]),
        "effect": row["effect"],
    }
