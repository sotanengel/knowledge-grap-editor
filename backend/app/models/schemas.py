from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NodeBase(BaseModel):
    label: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class NodeCreate(NodeBase):
    id: str


class NodeUpdate(BaseModel):
    label: str | None = None
    type: str | None = None
    properties: dict[str, Any] | None = None


class Node(NodeBase):
    id: str
    metadata: Metadata = Field(default_factory=Metadata)


class EdgeBase(BaseModel):
    subject: str
    predicate: str
    object: str
    properties: dict[str, Any] = Field(default_factory=dict)


class EdgeCreate(EdgeBase):
    id: str


class EdgeUpdate(BaseModel):
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    properties: dict[str, Any] | None = None


class Edge(EdgeBase):
    id: str
    metadata: Metadata = Field(default_factory=Metadata)


class ClassBase(BaseModel):
    label: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    parent_classes: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)


class ClassCreate(ClassBase):
    id: str
    force: bool = False


class ClassUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    aliases: list[str] | None = None
    parent_classes: list[str] | None = None
    examples: list[str] | None = None


class OntologyClass(ClassBase):
    id: str


class PropertyDef(BaseModel):
    id: str
    label: str = ""
    description: str = ""
    domain: list[str] = Field(default_factory=list)
    range: list[str] = Field(default_factory=list)
    required: bool = False
    aliases: list[str] = Field(default_factory=list)


class PropertyCreate(BaseModel):
    id: str
    label: str = ""
    description: str = ""
    domain: list[str] = Field(default_factory=list)
    range: list[str] = Field(default_factory=list)
    required: bool = False
    aliases: list[str] = Field(default_factory=list)


class RelationshipBase(BaseModel):
    label: str = ""
    description: str = ""
    domain: list[str] = Field(default_factory=list)
    range: list[str] = Field(default_factory=list)
    inverse: str | None = None
    aliases: list[str] = Field(default_factory=list)


class RelationshipCreate(RelationshipBase):
    id: str


class RelationshipUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    domain: list[str] | None = None
    range: list[str] | None = None
    inverse: str | None = None
    aliases: list[str] | None = None


class Relationship(RelationshipBase):
    id: str


class ValidationWarning(BaseModel):
    code: str
    message: str
    field: str | None = None


class SuggestResult(BaseModel):
    id: str
    label: str
    description: str = ""
    score: float
    parent_classes: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)


class SuggestResponse(BaseModel):
    results: list[SuggestResult]


class GraphSearchResult(BaseModel):
    nodes: list[Node]
    edges: list[Edge]


class NeighborResult(BaseModel):
    center: Node
    nodes: list[Node]
    edges: list[Edge]
    depth: int


class SchemaResponse(BaseModel):
    classes: list[OntologyClass]
    properties: list[PropertyDef]
    relationships: list[Relationship]


class SimilarClassWarning(BaseModel):
    message: str
    similar: list[SuggestResult]
