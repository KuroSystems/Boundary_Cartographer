"""API tests for the scenario + system endpoints (BE-12)."""

import json

import jsonschema

from tests.conftest import CONTRACT_DIR


def _load_schema(name: str) -> dict:
    return json.loads((CONTRACT_DIR / "schemas" / name).read_text(encoding="utf-8"))


def _health_schema() -> dict:
    import yaml

    spec = yaml.safe_load((CONTRACT_DIR / "openapi.yaml").read_text(encoding="utf-8"))
    return spec["components"]["schemas"]["HealthResponse"]


def test_health_happy_path_contract_shape(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    jsonschema.validate(body, _health_schema())
    assert body["status"] == "ok" and body["offline"] is True
    assert body["policy_engine"].startswith("local-rule-engine@")


def test_scenarios_demo_happy_path_matches_golden(client):
    resp = client.get("/api/v1/scenarios/demo")
    assert resp.status_code == 200
    body = resp.json()
    jsonschema.validate(body, _load_schema("scenario_response.schema.json"))
    golden_path = CONTRACT_DIR / "fixtures" / "demo_scenario.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    assert body == golden
    assert len(body["manifest"]["tools"]) == 4
    assert len(body["identities"]) == 2
    assert [r["id"] for r in body["policy"]["rules"]] == ["R1", "R2", "R3"]


def test_scenarios_demo_is_read_only(client):
    first = client.get("/api/v1/scenarios/demo").json()
    second = client.get("/api/v1/scenarios/demo").json()
    assert first == second  # no run, no side effects


def test_unknown_scenario_route_404(client):
    resp = client.get("/api/v1/scenarios/nope")
    assert resp.status_code == 404


def test_openapi_json_serves_exactly_the_five_documented_paths(client):
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    paths = sorted(resp.json()["paths"].keys())
    assert paths == ["/health", "/runs", "/runs/{run_id}",
                     "/runs/{run_id}/approval", "/scenarios/demo"]
    codes = resp.json()["components"]["schemas"]["ErrorCode"]["enum"]
    for code in ["SCENARIO_NOT_FOUND", "RUN_NOT_FOUND", "APPROVAL_ALREADY_DECIDED",
                 "INVALID_DECISION", "VALIDATION_ERROR"]:
        assert code in codes


def test_openapi_yaml_static_file_served(client):
    resp = client.get("/openapi.yaml")
    assert resp.status_code == 200
    assert "paths:" in resp.text
    assert "/runs/{run_id}/approval:" in resp.text
