import json
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from kg_mcp.server import app, search_nodes


@pytest.fixture
def client():
    return TestClient(app)


def test_mcp_health(client: TestClient):
    with patch("kg_mcp.server.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_instance
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_search_nodes_tool():
    with patch("kg_mcp.server._backend_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"nodes": [{"id": "apple", "label": "Apple"}]}
        result = await search_nodes("Apple")
        assert "Apple" in result
        mock_get.assert_called_once_with("/api/graph/search", {"q": "Apple"})


@pytest.mark.asyncio
async def test_get_schema_tool():
    from kg_mcp.server import get_schema

    with patch("kg_mcp.server._backend_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"classes": [], "properties": [], "relationships": []}
        result = await get_schema()
        data = json.loads(result)
        assert "classes" in data
