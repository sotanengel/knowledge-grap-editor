"""The ASGI application (§5.1).

One process serves the REST API, the SPARQL endpoint and -- once the front end
is built -- the static UI, which is what lets the whole product ship as a single
container with no compose file (P2).
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from ontoforge import __version__
from ontoforge.api.deps import RuntimeDep, require_auth
from ontoforge.api.routes import (
    analysis,
    entities,
    events,
    history,
    ontology,
    projects,
    sparql,
    transfer,
)
from ontoforge.api.schemas import Health
from ontoforge.config import Settings, load_settings
from ontoforge.projects.registry import ProjectRegistry
from ontoforge.runtime import Runtime

API_PREFIX = "/api/v1"
MCP_PATH = "/mcp"

TITLE = "OntoForge"
DESCRIPTION = (
    "Ontology and knowledge-graph authoring. The REST and SPARQL endpoints here "
    "are the read-write surface used by the UI; AI clients get a separate, "
    "strictly read-only MCP endpoint."
)


class TrailingSlashMiddleware:
    """Make ``/mcp`` and ``/mcp/`` the same endpoint.

    A mounted ASGI app owns ``<path>/...`` but not ``<path>`` itself, and the
    catch-all static mount answers the bare path before Starlette gets a chance
    to redirect. Rewriting the path here keeps the documented endpoint working
    without a redirect for clients to follow.
    """

    def __init__(self, app: ASGIApp, *, path: str) -> None:
        self.app = app
        self.path = path
        self.replacement = f"{path}/"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path") == self.path:
            scope = {
                **scope,
                "path": self.replacement,
                "raw_path": self.replacement.encode("ascii"),
            }
        await self.app(scope, receive, send)


def _health_router() -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/health", response_model=Health)
    def health(runtime: RuntimeDep) -> Health:
        return Health(
            status="ok",
            version=__version__,
            quads=runtime.store.count(),
            base_iri=runtime.settings.base_iri,
            reasoner=runtime.settings.reasoner,
            auth_required=runtime.settings.auth_required,
        )

    return router


def create_app(
    *,
    runtime: Runtime | None = None,
    settings: Settings | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    """Build the application.

    Pass ``runtime`` to reuse an already-open store (tests do this); otherwise
    one is opened for the lifetime of the process.
    """
    resolved_settings = settings or (runtime.settings if runtime is not None else load_settings())
    # When the app owns its runtime it owns a registry, so projects can be
    # switched at run time (FR-14). A caller-supplied runtime (tests) is used
    # as-is and stays on whichever project it was opened with.
    registry = ProjectRegistry(resolved_settings) if registry_owned(runtime) else None
    active: Runtime = registry.current if registry is not None else _required(runtime)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with contextlib.AsyncExitStack() as stack:
            manager = getattr(app.state, "mcp_session_manager", None)
            if manager is not None:
                await stack.enter_async_context(manager.run())
            try:
                yield
            finally:
                if registry is not None:
                    registry.close()

    app = FastAPI(
        title=TITLE,
        description=DESCRIPTION,
        version=__version__,
        lifespan=lifespan,
    )
    app.state.runtime = active
    if registry is not None:
        app.state.registry = registry

    guarded: list[Any] = [Depends(require_auth)]

    api = APIRouter(prefix=API_PREFIX, dependencies=guarded)
    api.include_router(_health_router())
    api.include_router(entities.router)
    api.include_router(ontology.router)
    api.include_router(transfer.router)
    api.include_router(analysis.router)
    api.include_router(projects.router)
    api.include_router(history.router)
    api.include_router(events.router)
    app.include_router(api)

    # The SPARQL protocol fixes the path, so it sits outside /api/v1 (§5.1).
    app.include_router(sparql.router, dependencies=guarded)

    _mount_mcp(app, active)

    resolved_static = static_dir or _bundled_static()
    if resolved_static is not None and resolved_static.is_dir():
        app.mount("/", StaticFiles(directory=resolved_static, html=True), name="ui")

    return app


def registry_owned(runtime: Runtime | None) -> bool:
    """Whether this app opens its own graph spaces, rather than reusing one."""
    return runtime is None


def _required(runtime: Runtime | None) -> Runtime:
    if runtime is None:  # pragma: no cover - guarded by registry_owned
        raise ValueError("a runtime is required when the app does not own a registry")
    return runtime


def _mount_mcp(app: FastAPI, runtime: Runtime) -> None:
    """Publish the read-only MCP endpoint at ``/mcp`` (§9.1).

    The tools see a read-only view: no write tool exists, and every mutating
    call is refused at the store wrapper (P4). Note that this in-process mount
    shares the API's handle rather than opening a second one -- pyoxigraph
    documents a second handle on a live database as undefined behaviour. The
    stdio transport, which runs as its own process, does get a genuine
    ``Store.read_only`` handle; see ``ontoforge mcp-stdio``.
    """
    from ontoforge.mcp.readonly import ReadOnlyGraph
    from ontoforge.mcp.server import create_server

    graph = ReadOnlyGraph.sharing(runtime.store, runtime.search, runtime.settings)
    server = create_server(graph, settings=runtime.settings)
    app.state.mcp_graph = graph

    # The sub-app routes its own root, so mounting it at /mcp puts the endpoint
    # exactly where §12.2 says it is. Requests arrive at a bare `/mcp`, which a
    # mount would normally answer with a redirect to `/mcp/` -- except that the
    # static-UI mount at `/` claims the bare path first and replies 405. The
    # middleware below rewrites the path before routing, so `/mcp` reaches the
    # sub-app directly and no redirect is involved at all.
    #
    # The session manager is created lazily by streamable_http_app(), so it can
    # only be picked up afterwards; the lifespan runs it.
    app.mount(MCP_PATH, server.streamable_http_app(streamable_http_path="/"))
    app.state.mcp_session_manager = server.session_manager
    app.add_middleware(TrailingSlashMiddleware, path=MCP_PATH)


def _bundled_static() -> Path | None:
    """The built UI, when it has been copied in next to the package."""
    candidate = Path(__file__).resolve().parent.parent / "static"
    return candidate if candidate.is_dir() else None
