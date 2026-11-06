"""S-01 placeholder smoke test: the app serves /api/v1/health."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_placeholder():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "boundary-cartographer"
