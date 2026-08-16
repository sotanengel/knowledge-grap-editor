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
    labels: list[str] = Field(default_factory=list)
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
    labels: list[str] = Field(default_factory=list)
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


# --- OWL 2 DL v2 schemas ---


class ClassExpressionSchema(BaseModel):
    kind: str
    iri: str | None = None
    operands: list["ClassExpressionSchema"] = Field(default_factory=list)
    operand: "ClassExpressionSchema | None" = None
    individuals: list[str] = Field(default_factory=list)
    on_property: str | None = None
    restriction_kind: str | None = None
    filler: "ClassExpressionSchema | str | None" = None
    cardinality: int | None = None


class AnnotationSchema(BaseModel):
    property: str
    value: str
    language: str | None = None
    datatype: str | None = None


class OwlClassV2(BaseModel):
    iri: str
    id: str
    label: str = ""
    labels: list[str] = Field(default_factory=list)
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    subclass_of: list[str | ClassExpressionSchema] = Field(default_factory=list)
    equivalent_class: list[ClassExpressionSchema] = Field(default_factory=list)
    disjoint_with: list[str | ClassExpressionSchema] = Field(default_factory=list)
    annotations: list[AnnotationSchema] = Field(default_factory=list)


class OwlClassCreateV2(BaseModel):
    id: str
    label: str = ""
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    subclass_of: list[str | ClassExpressionSchema] = Field(default_factory=list)
    equivalent_class: list[ClassExpressionSchema] = Field(default_factory=list)
    disjoint_with: list[str | ClassExpressionSchema] = Field(default_factory=list)
    force: bool = False


class OwlClassUpdateV2(BaseModel):
    label: str | None = None
    description: str | None = None
    aliases: list[str] | None = None
    examples: list[str] | None = None
    subclass_of: list[str | ClassExpressionSchema] | None = None
    equivalent_class: list[ClassExpressionSchema] | None = None
    disjoint_with: list[str | ClassExpressionSchema] | None = None


class OwlPropertyV2(BaseModel):
    iri: str
    id: str
    label: str = ""
    description: str = ""
    property_type: str
    domain: list[str] = Field(default_factory=list)
    range: list[str] = Field(default_factory=list)
    sub_property_of: list[str] = Field(default_factory=list)
    inverse_of: str | None = None
    characteristics: list[str] = Field(default_factory=list)
    editor_required: bool = False
    aliases: list[str] = Field(default_factory=list)


class OwlPropertyCreateV2(BaseModel):
    id: str
    label: str = ""
    description: str = ""
    property_type: str = "DatatypeProperty"
    domain: list[str] = Field(default_factory=list)
    range: list[str] = Field(default_factory=list)
    sub_property_of: list[str] = Field(default_factory=list)
    inverse_of: str | None = None
    characteristics: list[str] = Field(default_factory=list)
    editor_required: bool = False
    aliases: list[str] = Field(default_factory=list)


class OwlPropertyUpdateV2(BaseModel):
    label: str | None = None
    description: str | None = None
    domain: list[str] | None = None
    range: list[str] | None = None
    sub_property_of: list[str] | None = None
    inverse_of: str | None = None
    characteristics: list[str] | None = None
    editor_required: bool | None = None
    aliases: list[str] | None = None


class SchemaV2Response(BaseModel):
    classes: list[OwlClassV2]
    properties: list[OwlPropertyV2]
    annotations: list[AnnotationSchema] = Field(default_factory=list)


class TripleSchema(BaseModel):
    subject: str
    predicate: str
    object: str
    object_is_literal: bool = False
    literal_datatype: str | None = None
    literal_language: str | None = None
    source: str = "explicit"
    category: str = "tbox"


class InconsistencySchema(BaseModel):
    code: str
    message: str
    involved_iris: list[str] = Field(default_factory=list)


class ConsistencyReportSchema(BaseModel):
    consistent: bool
    inconsistencies: list[InconsistencySchema] = Field(default_factory=list)


ClassExpressionSchema.model_rebuild()
