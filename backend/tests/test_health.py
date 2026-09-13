from starlette.testclient import TestClient


def test_root_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data
    assert "environment" in data
    assert "version" in data


def test_api_v1_health_endpoint(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "allowed_formats" in data["details"]
    assert "wav" in data["details"]["allowed_formats"]
