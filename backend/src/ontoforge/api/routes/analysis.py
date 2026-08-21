"""Reasoning, validation and the vocabulary palette (§8, §10, FR-05/10/11)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pyoxigraph import NamedNode, Triple

from ontoforge.api.deps import RuntimeDep
from ontoforge.api.schemas import ExplainRequest, LoadVocabularies, ReasonRequest
from ontoforge.reasoning.rules import Profile, describe_profile
from ontoforge.reasoning.service import ReasonerService
from ontoforge.validation.service import ValidationService
from ontoforge.validation.shapes import ShapeSpec
from ontoforge.vocab import loader

router = APIRouter(tags=["analysis"])


# ---------------------------------------------------------------------- reasoning


@router.post("/reason")
def run_reasoner(body: ReasonRequest, runtime: RuntimeDep) -> dict[str, Any]:
    """Rebuild the inferred graph and report how much was derived (§10.1)."""
    try:
        summary = ReasonerService(runtime).run(profile=body.profile)
    except (KeyError, ValueError) as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"unknown reasoner profile {body.profile!r}",
        ) from error
    return {
        "profile": summary.profile,
        "derived": summary.derived,
        # What the closure produced but the canvas will not show, and why. Said
        # out loud so "why is that not there?" has an answer (§10.1).
        "suppressed": summary.suppressed,
        "suppressedByReason": summary.suppressed_by_reason,
    }


@router.get("/reason/profiles")
def list_profiles(runtime: RuntimeDep) -> dict[str, Any]:
    """The three profiles and the rules each applies, for the settings screen."""
    return {
        "current": runtime.settings.reasoner,
        "profiles": [
            {"name": profile.value, "rules": describe_profile(profile)} for profile in Profile
        ],
    }


@router.post("/reason/explain")
def explain(body: ExplainRequest, runtime: RuntimeDep) -> dict[str, Any]:
    """Why a derived triple holds: the rule and the premises (§10.1)."""
    try:
        triple = Triple(NamedNode(body.subject), NamedNode(body.predicate), NamedNode(body.object))
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    found = ReasonerService(runtime).explain(triple)
    if found is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "that triple was not derived; it is asserted directly or absent",
        )
    return {
        "triple": found.triple,
        "rule": found.rule,
        "premises": found.premises,
        "note": found.note,
    }


# ---------------------------------------------------------------------- validation


@router.post("/validate")
def validate(runtime: RuntimeDep) -> dict[str, Any]:
    """Run SHACL and report violations with a repair for each (§10.2, §7.3-3)."""
    return ValidationService(runtime).validate().as_dict()


@router.get("/shapes")
def list_shapes(runtime: RuntimeDep) -> dict[str, Any]:
    from ontoforge.store import graphs
    from ontoforge.validation.shapes import SH_TARGET_CLASS

    shapes = [
        {"@id": quad.subject.value, "targetClass": quad.object.value}
        for quad in runtime.store.quads_for_pattern(None, SH_TARGET_CLASS, None, graphs.SHAPES)
        if isinstance(quad.subject, NamedNode) and isinstance(quad.object, NamedNode)
    ]
    return {"shapes": sorted(shapes, key=lambda shape: shape["@id"])}


@router.put("/shapes/{name}")
def put_shape(name: str, body: ShapeSpec, runtime: RuntimeDep) -> dict[str, Any]:
    """Save a constraint the form produced, as SHACL (§10.2)."""
    if body.name != name:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"body names {body.name!r} but the path says {name!r}"
        )
    return ValidationService(runtime).save_shape(body)


@router.delete("/shapes/{name}")
def delete_shape(name: str, runtime: RuntimeDep) -> dict[str, int]:
    return {"removed": ValidationService(runtime).delete_shape(name)}


# ---------------------------------------------------------------------- vocabularies


@router.get("/vocabularies")
def list_vocabularies(runtime: RuntimeDep) -> dict[str, Any]:
    """What the left pane offers, and what is already loaded (§7.1)."""
    return {
        "available": loader.catalogue(),
        "loaded": loader.loaded_names(runtime.store),
        "defaults": list(loader.DEFAULT_VOCABULARIES),
    }


@router.post("/vocabularies")
def load_vocabularies(body: LoadVocabularies, runtime: RuntimeDep) -> dict[str, Any]:
    """Load bundled vocabularies. Nothing is fetched from the network (NFR-06)."""
    names = body.names or list(loader.DEFAULT_VOCABULARIES)
    try:
        loaded = loader.load(runtime.store, names)
    except loader.UnknownVocabularyError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    return {"loaded": loaded}
