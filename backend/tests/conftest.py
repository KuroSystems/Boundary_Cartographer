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
