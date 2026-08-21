"""Instance CRUD and label search (§8, FR-01 to FR-04, FR-08)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from ontoforge.api.deps import EntityDep, RuntimeDep
from ontoforge.api.schemas import CreateEntity, DeleteResult, PatchEntity
from ontoforge.entities import EntityNotFoundError

router = APIRouter(prefix="/entities", tags=["entities"])

MAX_LIMIT = 500


@router.get("")
def list_entities(
    entities: EntityDep,
    runtime: RuntimeDep,
    q: str = "",
    type: str | None = None,
    limit: int = Query(default=50, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Full-text label search, returned as a JSON-LD graph."""
    hits = entities.search(query=q, type_iri=type, limit=limit, offset=offset)
    return {"@context": runtime.context, "@graph": hits, "limit": limit, "offset": offset}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_entity(body: CreateEntity, entities: EntityDep) -> dict[str, Any]:
    try:
        return entities.create(
            label=body.label,
            types=body.types,
            properties=body.properties,
            comment=body.comment,
            language=body.language,
        )
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error


@router.get("/{iri:path}")
def get_entity(
    iri: str,
    entities: EntityDep,
    depth: int = Query(default=1, ge=1, le=5),
) -> dict[str, Any]:
    """The Concise Bounded Description of ``iri``, optionally with its neighbourhood."""
    try:
        return entities.get(iri, depth=depth)
    except EntityNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no entity at {iri}") from error


@router.patch("/{iri:path}")
def patch_entity(iri: str, body: PatchEntity, entities: EntityDep) -> dict[str, Any]:
    try:
        return entities.patch(
            iri,
            add=body.add,
            remove=body.remove,
            label=body.label,
            comment=body.comment,
            language=body.language,
        )
    except EntityNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no entity at {iri}") from error
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error


@router.delete("/{iri:path}")
def delete_entity(iri: str, entities: EntityDep) -> DeleteResult:
    try:
        return DeleteResult(removed=entities.delete(iri))
    except EntityNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no entity at {iri}") from error
