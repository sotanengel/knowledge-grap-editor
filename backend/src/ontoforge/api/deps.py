"""Shared request plumbing: the runtime handle and the optional bearer check."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from ontoforge.entities import EntityService
from ontoforge.io.csvmap import MappingStore
from ontoforge.io.service import ImportExportService
from ontoforge.ontology import OntologyService
from ontoforge.projects.registry import ProjectRegistry
from ontoforge.runtime import Runtime

MAPPINGS_DIRNAME = "mappings"


def registry_of(request: Request) -> ProjectRegistry:
    registry = getattr(request.app.state, "registry", None)
    if not isinstance(registry, ProjectRegistry):  # pragma: no cover - outside the lifespan
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "the runtime is not ready")
    return registry


def get_runtime(request: Request) -> Runtime:
    """The runtime of whichever project is open (FR-14).

    Resolved per request rather than captured once, so switching project takes
    effect immediately and no handler can keep hold of the previous graph.
    """
    registry = getattr(request.app.state, "registry", None)
    if isinstance(registry, ProjectRegistry):
        return registry.current

    runtime = getattr(request.app.state, "runtime", None)
    if not isinstance(runtime, Runtime):  # pragma: no cover - only outside the lifespan
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "the runtime is not ready")
    return runtime


RuntimeDep = Annotated[Runtime, Depends(get_runtime)]


def require_auth(request: Request, runtime: RuntimeDep) -> None:
    """Bearer check, active only when ``ONTOFORGE_AUTH_TOKEN`` is set (§13).

    Personal, loopback-only use needs no authentication; a token is what you set
    when you deliberately expose the instance to a LAN.
    """
    expected = runtime.settings.auth_token
    if expected is None:
        return

    header = request.headers.get("Authorization", "")
    scheme, _, presented = header.partition(" ")
    if not presented or scheme.lower() != "bearer":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "a bearer token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if presented != expected:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "the bearer token is not valid")


AuthDep = Annotated[None, Depends(require_auth)]


def get_entities(runtime: RuntimeDep) -> EntityService:
    return EntityService(runtime)


def get_ontology(runtime: RuntimeDep) -> OntologyService:
    return OntologyService(runtime)


def get_transfer(runtime: RuntimeDep) -> ImportExportService:
    return ImportExportService(runtime)


def get_mappings(runtime: RuntimeDep) -> MappingStore:
    return MappingStore(runtime.settings.data_dir / MAPPINGS_DIRNAME)


EntityDep = Annotated[EntityService, Depends(get_entities)]
OntologyDep = Annotated[OntologyService, Depends(get_ontology)]
TransferDep = Annotated[ImportExportService, Depends(get_transfer)]
MappingDep = Annotated[MappingStore, Depends(get_mappings)]
