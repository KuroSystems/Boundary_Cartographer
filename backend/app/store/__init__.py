"""SQLite store package (BE-03)."""

from .db import SCHEMA_VERSION, connect, init_db, open_db
from .repository import (
    ApprovalConflict,
    append_evidence,
    compute_hash,
    create_approval_item,
    decide_approval,
    get_approval_state,
    get_run,
    insert_run,
    list_evidence,
)

__all__ = [
    "SCHEMA_VERSION",
    "ApprovalConflict",
    "append_evidence",
    "compute_hash",
    "connect",
    "create_approval_item",
    "decide_approval",
    "get_approval_state",
    "get_run",
    "init_db",
    "insert_run",
    "list_evidence",
    "open_db",
]
