"""Health endpoint serves the frozen contract HealthResponse (BE-11)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_contract_shape():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "ok",
        "offline": True,
        "policy_engine": "local-rule-engine@1.0.0",
    }
