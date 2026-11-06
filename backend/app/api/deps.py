"""Dependency wiring (BE-11): repository/DB access.

The SQLite path comes from the BOUNDARY_DB_PATH env var (default
./var/boundary.db, relative to the backend cwd). Tests override it with a
tmp_path database. Connections are opened per request and closed on teardown.
"""

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends

from app.store.db import open_db

DEFAULT_DB_PATH = "./var/boundary.db"


def get_db_path() -> Path:
    raw = os.environ.get("BOUNDARY_DB_PATH", DEFAULT_DB_PATH)
    path = Path(raw)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_db() -> Iterator[sqlite3.Connection]:
    conn = open_db(get_db_path())
    try:
        yield conn
    finally:
        conn.close()


DbConn = Depends(get_db)
