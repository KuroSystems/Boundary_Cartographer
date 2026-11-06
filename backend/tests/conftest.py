"""Shared test fixtures (BE-12).

- autouse `_isolated_db`: every test gets a fresh SQLite DB under tmp_path via
  BOUNDARY_DB_PATH, so a test run leaves no artifacts outside tmp_path.
- `client`: FastAPI TestClient bound to the app factory.
- `fixtures`: the loaded demo fixtures.
- `run_factory`: helper that POSTs /api/v1/runs and returns (response, run_id).
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.fixtures import load_fixtures
from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = REPO_ROOT / "contract"


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("BOUNDARY_DB_PATH", str(tmp_path / "test.db"))
    yield tmp_path


# ---------------------------------------------------------------------------
# BE-13 global safety guards — active for the WHOLE suite:
# 1. no network: socket.socket / socket.create_connection raise immediately;
# 2. no writes outside tmp_path (protects app/fixtures and the rest of the repo).
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Block all outbound network while keeping local socketpair() working.

    Patching socket.socket itself would break asyncio's internal socketpair
    (used by the ASGI TestClient), so the guard trips at connect/DNS time —
    any real network attempt still fails immediately and loudly.
    """
    import socket

    def _blocked(*args, **kwargs):
        raise AssertionError(
            "network access attempted during the test suite — the MVP is fully "
            "offline after bootstrap; this guard tripped"
        )

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)
    yield


@pytest.fixture(autouse=True)
def _no_writes_outside_tmp(tmp_path, monkeypatch):
    import builtins
    import io

    real_open = builtins.open
    tmp_root = str(tmp_path.resolve())

    def _guarded_open(file, mode="r", *args, **kwargs):
        if any(m in mode for m in ("w", "a", "x", "+")):
            try:
                resolved = str(Path(file).resolve())
            except (TypeError, ValueError):
                resolved = str(file)
            if not resolved.startswith(tmp_root):
                raise AssertionError(
                    f"write outside tmp_path blocked: {file} (mode={mode!r}) — "
                    "tests must not modify the repo or fixtures"
                )
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _guarded_open)
    monkeypatch.setattr(io, "open", _guarded_open)
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def fixtures():
    return load_fixtures()


@pytest.fixture
def run_factory(client):
    def _create(scenario_id: str = "demo-v1"):
        resp = client.post("/api/v1/runs", json={"scenario_id": scenario_id})
        assert resp.status_code == 201, resp.text
        return resp, resp.json()["run_id"]

    return _create


def db_path() -> str:
    return os.environ["BOUNDARY_DB_PATH"]
