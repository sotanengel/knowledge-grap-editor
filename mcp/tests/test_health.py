from starlette.testclient import TestClient

from kg_mcp.server import app


def test_mcp_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "backend_connected" in data
