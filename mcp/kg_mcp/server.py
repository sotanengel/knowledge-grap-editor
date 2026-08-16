"""Knowledge Graph MCP Server - scaffold health endpoint."""

import os

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

BACKEND_URL = os.environ.get("KG_BACKEND_URL", "http://127.0.0.1:8000")


async def health(_request):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{BACKEND_URL}/health", timeout=5.0)
            backend_ok = resp.status_code == 200
    except httpx.HTTPError:
        backend_ok = False
    return JSONResponse({"status": "ok", "backend_connected": backend_ok})


app = Starlette(routes=[Route("/health", health)])


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
