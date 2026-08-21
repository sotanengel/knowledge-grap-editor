"""Class and property definitions (§8, FR-03)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from ontoforge.api.deps import OntologyDep
from ontoforge.api.schemas import CreateClass, CreateProperty, RenameTerm
from ontoforge.ontology import TermNotFoundError

router = APIRouter(prefix="/ontology", tags=["ontology"])


@router.get("")
def get_tree(ontology: OntologyDep) -> dict[str, Any]:
    """The class hierarchy and property list that fill the left pane (§7.1)."""
    return ontology.tree()


@router.post("/classes", status_code=status.HTTP_201_CREATED)
def create_class(body: CreateClass, ontology: OntologyDep) -> dict[str, Any]:
    try:
        return ontology.add_class(label=body.label, parents=body.parents, comment=body.comment)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error


@router.get("/properties")
def list_properties(ontology: OntologyDep, domain: str | None = None) -> dict[str, Any]:
    """Properties on offer, narrowed to those whose domain fits (§7.2)."""
    return {"properties": ontology.candidate_properties(domain=domain)}


@router.post("/properties", status_code=status.HTTP_201_CREATED)
def create_property(body: CreateProperty, ontology: OntologyDep) -> dict[str, Any]:
    try:
        return ontology.add_property(
            label=body.label,
            kind=body.kind,
            parents=body.parents,
            domain=body.domain,
            range_=body.range,
            comment=body.comment,
        )
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error


@router.post("/rename")
def rename_term(body: RenameTerm, ontology: OntologyDep) -> dict[str, Any]:
    try:
        return ontology.rename(body.iri, body.label)
    except TermNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no term at {body.iri}") from error
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
