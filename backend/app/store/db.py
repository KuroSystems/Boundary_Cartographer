"""SQLite connection management (BE-03).

Stdlib sqlite3 only (no ORM). Every connection gets WAL journal mode and
foreign keys ON; `init_db` applies schema.sql and records the schema version.
"""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
SCHEMA_VERSION = 1


def connect(db_path: str | Path = ":memory:") -> sqlite3.Connection:
    """Open a connection with WAL + foreign keys enabled."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Apply schema.sql (idempotent) and record the schema version."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute(
        "INSERT OR IGNORE INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
    )
    conn.commit()


def open_db(db_path: str | Path = ":memory:") -> sqlite3.Connection:
    """connect + init_db in one call."""
    conn = connect(db_path)
    init_db(conn)
    return conn
