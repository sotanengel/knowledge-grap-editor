"""Request and response bodies for the REST API (§8)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PropertyMap = dict[str, Any]


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateEntity(_Body):
    """``POST /entities``."""

    label: str
    types: list[str] = Field(default_factory=list)
    properties: PropertyMap = Field(default_factory=dict)
    comment: str | None = None
    language: str = "ja"

    @field_validator("label")
    @classmethod
    def _label_must_have_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("label must not be empty")
        return value


class PatchEntity(_Body):
    """``PATCH /entities/{iri}``: the triples to add and remove."""

    add: PropertyMap = Field(default_factory=dict)
    remove: PropertyMap = Field(default_factory=dict)
    label: str | None = None
    comment: str | None = None
    language: str = "ja"


class CreateClass(_Body):
    """``POST /ontology/classes``."""

    label: str
    parents: list[str] = Field(default_factory=list)
    comment: str | None = None


class CreateProperty(_Body):
    """``POST /ontology/properties``."""

    label: str
    kind: Literal["object", "datatype"] = "object"
    parents: list[str] = Field(default_factory=list)
    domain: str | None = None
    range: str | None = None
    comment: str | None = None


class RenameTerm(_Body):
    """``POST /ontology/rename``: the IRI moves, every reference follows (§6.2)."""

    iri: str
    label: str


class DeleteResult(BaseModel):
    removed: int


class HistoryEntry(BaseModel):
    """One recorded change."""

    seq: int
    id: str
    actor: str
    timestamp: str
    additions: int
    deletions: int
    inverse_of: str | None = None


class HistoryPage(BaseModel):
    entries: list[HistoryEntry]
    can_undo: bool
    can_redo: bool


class ImportSummary(BaseModel):
    quads: int
    rows: int
    iris: list[str]
    format: str


class MappingNames(BaseModel):
    names: list[str]


class Health(BaseModel):
    status: Literal["ok"]
    version: str
    quads: int
    base_iri: str
    reasoner: str
    auth_required: bool
