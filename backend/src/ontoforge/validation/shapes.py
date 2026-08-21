"""Building SHACL shapes from a form, not from typed Turtle (§10.2).

The user says "a person must have exactly one birth date, and it must be a
date". This turns that into SHACL behind their back, which is the whole point of
P1: the standard underneath, hidden by the interface.
"""

from __future__ import annotations

from typing import Literal as LiteralType

from pydantic import BaseModel, ConfigDict, Field
from pyoxigraph import Literal, NamedNode, Quad

from ontoforge.literals import XSD_INTEGER, XSD_STRING
from ontoforge.namespaces import RDF_TYPE, RDFS_LABEL, SH
from ontoforge.store import graphs

SH_NODE_SHAPE = NamedNode(f"{SH}NodeShape")
SH_TARGET_CLASS = NamedNode(f"{SH}targetClass")
SH_PROPERTY = NamedNode(f"{SH}property")
SH_PATH = NamedNode(f"{SH}path")
SH_MIN_COUNT = NamedNode(f"{SH}minCount")
SH_MAX_COUNT = NamedNode(f"{SH}maxCount")
SH_DATATYPE = NamedNode(f"{SH}datatype")
SH_CLASS = NamedNode(f"{SH}class")
SH_NODE_KIND = NamedNode(f"{SH}nodeKind")
SH_IRI = NamedNode(f"{SH}IRI")
SH_PATTERN = NamedNode(f"{SH}pattern")
SH_MESSAGE = NamedNode(f"{SH}message")
SH_CLOSED = NamedNode(f"{SH}closed")
SH_SEVERITY = NamedNode(f"{SH}severity")
SH_VIOLATION = NamedNode(f"{SH}Violation")
SH_WARNING = NamedNode(f"{SH}Warning")

XSD_BOOLEAN_TRUE = Literal("true", datatype=NamedNode("http://www.w3.org/2001/XMLSchema#boolean"))

Severity = LiteralType["violation", "warning"]

_SEVERITY_NODE: dict[str, NamedNode] = {"violation": SH_VIOLATION, "warning": SH_WARNING}


class PropertyConstraint(BaseModel):
    """One rule about one property of a class."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    min_count: int | None = Field(default=None, ge=0)
    max_count: int | None = Field(default=None, ge=0)
    datatype: str | None = None
    class_: str | None = Field(default=None, alias="class")
    pattern: str | None = None
    message: str | None = None
    severity: Severity = "violation"


class ShapeSpec(BaseModel):
    """What the constraint form produces before it becomes SHACL."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    target_class: str
    label: str | None = None
    properties: list[PropertyConstraint] = Field(default_factory=list)
    closed: bool = False


def shape_iri(base_iri: str, name: str) -> NamedNode:
    return NamedNode(f"{base_iri}shape/{name}")


def to_quads(spec: ShapeSpec, *, base_iri: str) -> list[Quad]:
    """The SHACL quads for ``spec``, ready for ``urn:ontoforge:shapes``."""
    graph = graphs.SHAPES
    shape = shape_iri(base_iri, spec.name)
    quads = [
        Quad(shape, RDF_TYPE, SH_NODE_SHAPE, graph),
        Quad(shape, SH_TARGET_CLASS, NamedNode(spec.target_class), graph),
    ]
    if spec.label:
        quads.append(Quad(shape, RDFS_LABEL, Literal(spec.label, language="ja"), graph))
    if spec.closed:
        quads.append(Quad(shape, SH_CLOSED, XSD_BOOLEAN_TRUE, graph))

    for index, constraint in enumerate(spec.properties):
        node = NamedNode(f"{shape.value}/p{index}")
        quads.append(Quad(shape, SH_PROPERTY, node, graph))
        quads.append(Quad(node, SH_PATH, NamedNode(constraint.path), graph))
        if constraint.min_count is not None:
            quads.append(
                Quad(
                    node,
                    SH_MIN_COUNT,
                    Literal(str(constraint.min_count), datatype=XSD_INTEGER),
                    graph,
                )
            )
        if constraint.max_count is not None:
            quads.append(
                Quad(
                    node,
                    SH_MAX_COUNT,
                    Literal(str(constraint.max_count), datatype=XSD_INTEGER),
                    graph,
                )
            )
        if constraint.datatype:
            quads.append(Quad(node, SH_DATATYPE, NamedNode(constraint.datatype), graph))
        if constraint.class_:
            quads.append(Quad(node, SH_CLASS, NamedNode(constraint.class_), graph))
            quads.append(Quad(node, SH_NODE_KIND, SH_IRI, graph))
        if constraint.pattern:
            quads.append(
                Quad(node, SH_PATTERN, Literal(constraint.pattern, datatype=XSD_STRING), graph)
            )
        if constraint.message:
            quads.append(Quad(node, SH_MESSAGE, Literal(constraint.message, language="ja"), graph))
        quads.append(Quad(node, SH_SEVERITY, _SEVERITY_NODE[constraint.severity], graph))

    return quads
