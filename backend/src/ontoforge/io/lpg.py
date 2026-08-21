"""Reading property-graph exports back in (§14 Phase 3).

PR2 could write GraphML and node/edge CSV so the data could leave for Gephi,
yEd or Neo4j. This is the return leg: the same shapes read back, so a graph can
go out to another tool, be worked on there, and come home.

The round trip is designed to be lossless for what the property-graph view can
carry -- nodes, their labels and types, literal attributes, and typed edges. It
cannot carry what the shape has no room for (named graphs, language tags,
quoted-triple annotations), and this says so rather than pretending otherwise:
:func:`round_trip_warnings` lists what a given export would drop.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from pyoxigraph import Literal, NamedNode, Quad, Triple

from ontoforge.io.exporters import EDGES_FILENAME, GRAPHML_NS, NODES_FILENAME
from ontoforge.literals import make_literal
from ontoforge.namespaces import RDF_TYPE, RDFS_LABEL
from ontoforge.store import graphs

#: Attribute keys the exporters write about the node itself, not as data.
RESERVED_NODE_KEYS = frozenset({"label", "types"})
ATTRIBUTE_SEPARATOR = " "


class LpgParseError(ValueError):
    """Raised when a property-graph file cannot be read."""


@dataclass(slots=True)
class LpgNode:
    """One vertex as it appears in a property-graph file."""

    iri: str
    label: str = ""
    types: list[str] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class LpgEdge:
    """One relation."""

    source: str
    target: str
    predicate: str


@dataclass(slots=True)
class LpgGraph:
    """What was read out of a file, before it becomes RDF."""

    nodes: list[LpgNode] = field(default_factory=list)
    edges: list[LpgEdge] = field(default_factory=list)


# ---------------------------------------------------------------------- GraphML


def read_graphml(payload: str | bytes) -> LpgGraph:
    """Read a GraphML document written by :func:`ontoforge.io.exporters.to_graphml`."""
    try:
        root = ET.fromstring(payload if isinstance(payload, str) else payload.decode("utf-8"))
    except ET.ParseError as error:
        raise LpgParseError(f"not valid GraphML: {error}") from error

    keys = {
        element.get("id", ""): element.get("attr.name", "")
        for element in root.findall(f"{{{GRAPHML_NS}}}key")
    }
    graph_element = root.find(f"{{{GRAPHML_NS}}}graph")
    if graph_element is None:
        raise LpgParseError("the GraphML document has no <graph>")

    graph = LpgGraph()
    for element in graph_element.findall(f"{{{GRAPHML_NS}}}node"):
        iri = element.get("id")
        if not iri:
            continue
        node = LpgNode(iri=iri)
        for data in element.findall(f"{{{GRAPHML_NS}}}data"):
            name = keys.get(data.get("key", ""), "")
            value = data.text or ""
            if name == "label":
                node.label = value
            elif name == "types":
                node.types = [entry for entry in value.split(ATTRIBUTE_SEPARATOR) if entry]
            elif name:
                node.attributes[name] = value
        graph.nodes.append(node)

    for element in graph_element.findall(f"{{{GRAPHML_NS}}}edge"):
        source, target = element.get("source"), element.get("target")
        if not source or not target:
            continue
        predicate = ""
        for data in element.findall(f"{{{GRAPHML_NS}}}data"):
            if keys.get(data.get("key", ""), "") == "predicate":
                predicate = data.text or ""
        if predicate:
            graph.edges.append(LpgEdge(source=source, target=target, predicate=predicate))

    return graph


# ---------------------------------------------------------------------- CSV pair


def read_csv_tables(payload: bytes) -> LpgGraph:
    """Read the zip of ``nodes.csv`` and ``edges.csv`` the exporter writes."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as error:
        raise LpgParseError("not a zip archive of node and edge tables") from error

    names = set(archive.namelist())
    missing = {NODES_FILENAME, EDGES_FILENAME} - names
    if missing:
        raise LpgParseError(f"the archive is missing: {', '.join(sorted(missing))}")

    graph = LpgGraph()
    for row in csv.DictReader(io.StringIO(archive.read(NODES_FILENAME).decode("utf-8"))):
        iri = (row.get(":ID") or "").strip()
        if not iri:
            continue
        node = LpgNode(iri=iri, label=(row.get("label") or "").strip())
        for column, value in row.items():
            if column in (":ID", "label", ":LABEL") or not column or not value:
                continue
            node.attributes[column] = value
        graph.nodes.append(node)

    for row in csv.DictReader(io.StringIO(archive.read(EDGES_FILENAME).decode("utf-8"))):
        source = (row.get(":START_ID") or "").strip()
        target = (row.get(":END_ID") or "").strip()
        predicate = (row.get("predicate") or "").strip()
        if source and target and predicate:
            graph.edges.append(LpgEdge(source=source, target=target, predicate=predicate))

    return graph


# ---------------------------------------------------------------------- to RDF


def to_quads(
    graph: LpgGraph,
    *,
    attribute_namespace: str,
    target: NamedNode = graphs.DATA,
    language: str = "ja",
) -> list[Quad]:
    """Turn a property graph into quads.

    Attribute keys came out of the export as local names, so they go back under
    ``attribute_namespace`` -- which is the same ``{base}ont#`` they were minted
    into in the first place.
    """
    quads: list[Quad] = []
    for node in graph.nodes:
        subject = _node(node.iri)
        if node.label:
            quads.append(
                Quad(subject, RDFS_LABEL, make_literal(node.label, language=language), target)
            )
        quads.extend(Quad(subject, RDF_TYPE, _node(type_iri), target) for type_iri in node.types)
        for key, value in node.attributes.items():
            if key in RESERVED_NODE_KEYS or not value:
                continue
            predicate = _node(key if "://" in key else f"{attribute_namespace}{key}")
            quads.append(Quad(subject, predicate, make_literal(value), target))

    for edge in graph.edges:
        quads.append(Quad(_node(edge.source), _node(edge.predicate), _node(edge.target), target))
    return quads


def _node(value: str) -> NamedNode:
    try:
        return NamedNode(value)
    except ValueError as error:
        raise LpgParseError(f"{value!r} is not a usable IRI") from error


# ---------------------------------------------------------------------- honesty


def round_trip_warnings(quads: Sequence[Quad]) -> list[str]:
    """What a property-graph export of ``quads`` would fail to bring back.

    Better to say this up front than to let someone discover it after they have
    edited the export somewhere else.
    """
    warnings: list[str] = []

    tagged = sum(1 for quad in quads if isinstance(quad.object, Literal) and quad.object.language)
    if tagged:
        warnings.append(
            f"言語タグ付きリテラル {tagged} 件は、書き戻し時に既定の言語タグになります。"
        )

    quoted = sum(
        1 for quad in quads if isinstance(quad.subject, Triple) or isinstance(quad.object, Triple)
    )
    if quoted:
        warnings.append(
            f"エッジ属性（出典・確信度）{quoted} 件は、プロパティグラフ形式には持ち出せません。"
        )

    named = {quad.graph_name for quad in quads}
    if len(named) > 1:
        warnings.append(
            f"{len(named)} 個の名前付きグラフは 1 つに畳まれ、書き戻し時に区別できません。"
        )

    return warnings


def summarise(graph: LpgGraph) -> dict[str, int]:
    return {"nodes": len(graph.nodes), "edges": len(graph.edges)}


def node_iris(graph: LpgGraph) -> Iterable[str]:
    return (node.iri for node in graph.nodes)
