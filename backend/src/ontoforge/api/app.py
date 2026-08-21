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

from ontoforge import __version__
from ontoforge.api.deps import RuntimeDep, require_auth
from ontoforge.api.routes import entities, events, history, ontology, sparql, transfer
from ontoforge.api.schemas import Health
from ontoforge.config import Settings, load_settings
from ontoforge.runtime import Runtime

API_PREFIX = "/api/v1"

TITLE = "OntoForge"
DESCRIPTION = (
    "Ontology and knowledge-graph authoring. The REST and SPARQL endpoints here "
    "are the read-write surface used by the UI; AI clients get a separate, "
    "strictly read-only MCP endpoint."
)


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
    owns_runtime = runtime is None

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if owns_runtime:
            app.state.runtime = Runtime.create(settings or load_settings())
        try:
            yield
        finally:
            if owns_runtime:
                app.state.runtime.close()

    app = FastAPI(
        title=TITLE,
        description=DESCRIPTION,
        version=__version__,
        lifespan=lifespan,
    )
    if runtime is not None:
        app.state.runtime = runtime

    guarded: list[Any] = [Depends(require_auth)]

    api = APIRouter(prefix=API_PREFIX, dependencies=guarded)
    api.include_router(_health_router())
    api.include_router(entities.router)
    api.include_router(ontology.router)
    api.include_router(transfer.router)
    api.include_router(history.router)
    api.include_router(events.router)
    app.include_router(api)

    # The SPARQL protocol fixes the path, so it sits outside /api/v1 (§5.1).
    app.include_router(sparql.router, dependencies=guarded)

    resolved_static = static_dir or _bundled_static()
    if resolved_static is not None and resolved_static.is_dir():
        app.mount("/", StaticFiles(directory=resolved_static, html=True), name="ui")

    return app


def _bundled_static() -> Path | None:
    """The built UI, when it has been copied in next to the package."""
    candidate = Path(__file__).resolve().parent.parent / "static"
    return candidate if candidate.is_dir() else None
