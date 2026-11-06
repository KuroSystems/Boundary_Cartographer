"""API tests for POST /runs and GET /runs/{run_id} (BE-12)."""

import json
import sqlite3

import jsonschema

from tests.conftest import CONTRACT_DIR, db_path


def _run_schema() -> dict:
    return json.loads(
        (CONTRACT_DIR / "schemas" / "run_response.schema.json").read_text(encoding="utf-8")
    )


def test_create_run_201_persists_and_get_is_byte_identical(client, run_factory):
    resp, run_id = run_factory()
    assert resp.status_code == 201
    jsonschema.validate(resp.json(), _run_schema())

    fetched = client.get(f"/api/v1/runs/{run_id}")
    assert fetched.status_code == 200
    assert fetched.json() == resp.json()

    raw = sqlite3.connect(db_path()).execute(
        "SELECT payload FROM runs WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    assert fetched.content.decode() == raw  # byte-identical to the stored payload

    conn = sqlite3.connect(db_path())
    n_evidence = conn.execute(
        "SELECT COUNT(*) FROM evidence WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    assert n_evidence == len(resp.json()["evidence"])
    n_approvals = conn.execute(
        "SELECT COUNT(*) FROM approvals WHERE run_id = ?", (run_id,)
    ).fetchone()[0]
    assert n_approvals == 1  # ap-1 persisted as pending


def test_create_run_statuses_match_contract_expectations(client, run_factory):
    resp, _ = run_factory()
    by_id = {p["path_id"]: p["status"] for p in resp.json()["paths"]}
    assert by_id == {"P1": "blocked", "P2": "blocked", "P3": "allowed",
                     "P4": "disproved", "P5": "allowed"}
    diff = resp.json()["policy_diff"]
    assert diff["before"]["policy_id"] == "demo-policy-v1"
    assert diff["after"]["policy_id"] == "demo-policy-v2-simulated"
    assert diff["simulated"] is True


def test_create_run_unknown_scenario_400_scenario_not_found(client):
    resp = client.post("/api/v1/runs", json={"scenario_id": "demo-v9"})
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "SCENARIO_NOT_FOUND"
    assert err["details"] == {"scenario_id": "demo-v9"}


def test_create_run_invalid_body_422_validation_error(client):
    resp = client.post("/api/v1/runs", json={"scenario_id": "demo-v1",
                                              "options": {"include_disproved": "maybe"}})
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert err["details"]["issues"]

    resp = client.post("/api/v1/runs", json={})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    resp = client.post("/api/v1/runs", json={"scenario_id": "demo-v1", "bogus": 1})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_run_unknown_404_run_not_found(client):
    resp = client.get("/api/v1/runs/DOESNOTEXIST")
    assert resp.status_code == 404
    err = resp.json()["error"]
    assert err["code"] == "RUN_NOT_FOUND"
    assert err["details"] == {"run_id": "DOESNOTEXIST"}
