"""A property-graph view of the RDF, shared by the non-RDF exporters (§4.1).

GraphML, the node/edge CSV pair and Mermaid all want the same thing: nodes with
attributes, and edges between them. Literals become node attributes, IRI objects
become edges, and ``rdf:type`` becomes the node's type list.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from pyoxigraph import Literal, NamedNode, Quad

from ontoforge.jsonld import label_of
from ontoforge.namespaces import LABEL_PREDICATES, RDF_TYPE
from ontoforge.store import graphs
from ontoforge.store.store import GraphStore


@dataclass(slots=True)
class GraphNode:
    """One vertex of the property-graph view."""

    iri: str
    label: str = ""
    types: list[str] = field(default_factory=list)
    attributes: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """One relation between two vertices."""

    source: str
    target: str
    predicate: str
    label: str


@dataclass(slots=True)
class GraphView:
    """The whole projection."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]

    @property
    def attribute_keys(self) -> list[str]:
        keys = {key for node in self.nodes for key in node.attributes}
        return sorted(keys)


def local_name(iri: str) -> str:
    """The readable tail of an IRI, for display when there is no label."""
    for separator in ("#", "/", ":"):
        _, found, tail = iri.rpartition(separator)
        if found and tail:
            return tail
    return iri


def build_view(
    store: GraphStore,
    named_graphs: Sequence[NamedNode] = graphs.DEFAULT_EXPORT,
) -> GraphView:
    """Project ``named_graphs`` into nodes and edges."""
    quads = [
        quad
        for graph in named_graphs
        for quad in store.quads_for_pattern(None, None, None, graph)
        # Quoted-triple annotations describe edges, not nodes; they are carried
        # by the RDF exports and would only confuse a property-graph consumer.
        if isinstance(quad.subject, NamedNode)
    ]
    return view_from_quads(quads)


def view_from_quads(quads: Iterable[Quad]) -> GraphView:
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    labels: dict[str, str] = {}

    materialised = list(quads)
    for quad in materialised:
        if (
            quad.predicate in LABEL_PREDICATES
            and isinstance(quad.object, Literal)
            and isinstance(quad.subject, NamedNode)
        ):
            labels.setdefault(quad.subject.value, quad.object.value)

    def node_for(iri: str) -> GraphNode:
        if iri not in nodes:
            nodes[iri] = GraphNode(iri=iri, label=labels.get(iri, local_name(iri)))
        return nodes[iri]

    for quad in materialised:
        if not isinstance(quad.subject, NamedNode):
            continue
        subject = node_for(quad.subject.value)

        if quad.predicate == RDF_TYPE and isinstance(quad.object, NamedNode):
            subject.types.append(quad.object.value)
            continue
        if isinstance(quad.object, NamedNode):
            node_for(quad.object.value)
            edges.append(
                GraphEdge(
                    source=quad.subject.value,
                    target=quad.object.value,
                    predicate=quad.predicate.value,
                    label=local_name(quad.predicate.value),
                )
            )
            continue
        if isinstance(quad.object, Literal):
            subject.attributes.setdefault(local_name(quad.predicate.value), []).append(
                quad.object.value
            )

    for iri, node in nodes.items():
        node.label = labels.get(iri, node.label)
    return GraphView(nodes=list(nodes.values()), edges=edges)


def label_for(store: GraphStore, node: NamedNode) -> str:
    """The label of ``node``, falling back to its local name."""
    found = label_of(store.quads_for_pattern(node, None, None, None))
    return found if found is not None else local_name(node.value)
