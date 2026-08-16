"""Knowledge Graph MCP Server."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
import uvicorn
from mcp.server.mcpserver.server import MCPServer
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

BACKEND_URL = os.environ.get("KG_BACKEND_URL", "http://127.0.0.1:8000")

mcp = MCPServer("knowledge-graph")


async def _backend_get(path: str, params: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND_URL}{path}", params=params, timeout=30.0)
        resp.raise_for_status()
        if resp.status_code == 204:
            return None
        return resp.json()


@mcp.tool(description="ノードをキーワードで検索する")
async def search_nodes(query: str) -> str:
    data = await _backend_get("/api/graph/search", {"q": query})
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool(description="指定 ID のノードを取得する")
async def get_node(node_id: str) -> str:
    data = await _backend_get(f"/api/nodes/{node_id}")
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool(description="ノード周辺のグラフを取得する")
async def get_neighbors(node_id: str, depth: int = 2) -> str:
    data = await _backend_get(f"/api/nodes/{node_id}/neighbors", {"depth": depth})
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool(description="型を指定してノードを検索する")
async def search_by_type(type: str) -> str:
    data = await _backend_get("/api/nodes", {"type": type})
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool(description="利用可能なオントロジーを取得する")
async def get_schema() -> str:
    data = await _backend_get("/api/ontology/v2/schema")
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool(description="2つのノード間の関係を探索する")
async def find_relationship(source: str, target: str) -> str:
    data = await _backend_get("/api/graph/relationship", {"source": source, "target": target})
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.resource("ontology://schema")
async def schema_resource() -> str:
    data = await _backend_get("/api/ontology/v2/schema")
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.resource("ontology://classes")
async def classes_resource() -> str:
    data = await _backend_get("/api/ontology/classes")
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.resource("ontology://properties")
async def properties_resource() -> str:
    data = await _backend_get("/api/ontology/v2/properties")
    return json.dumps(data, ensure_ascii=False, indent=2)


async def health(_request: Request):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BACKEND_URL}/health", timeout=5.0)
            backend_ok = resp.status_code == 200
    except httpx.HTTPError:
        backend_ok = False
    return JSONResponse({"status": "ok", "backend_connected": backend_ok})


sse_app = mcp.sse_app(host="0.0.0.0")

app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", app=sse_app),
    ]
)


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
