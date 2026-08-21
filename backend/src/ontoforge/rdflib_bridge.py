"""The one crossing between pyoxigraph and rdflib.

Two things in this project need rdflib: pySHACL (§10.2) and owlrl (§10.1, §5.3).
The store is pyoxigraph, so both cross here rather than each growing its own
conversion.

N-Triples is the cheapest serialisation both sides agree on. Nothing about the
crossing is clever, and that is the point -- it is a place to put the one
awkward fact about it, which is that rdflib cannot read RDF 1.2 triple terms.
"""

from __future__ import annotations

from collections.abc import Iterable

from pyoxigraph import DefaultGraph, NamedNode, Quad, RdfFormat, Triple, parse, serialize
from rdflib import BNode as RdflibBNode
from rdflib import Graph as RdflibGraph
from rdflib import URIRef as RdflibURIRef

GraphName = NamedNode | DefaultGraph


def to_rdflib(quads: Iterable[Quad]) -> RdflibGraph:
    """Flatten quads into a single rdflib graph.

    Quads carrying an RDF 1.2 triple term are dropped: rdflib cannot parse
    ``<<( ... )>>``, and neither SHACL nor OWL 2 RL has anything to say about a
    reified statement. In practice these are the reasoner's own markers and the
    edge-metadata reifiers, neither of which is data to reason over.
    """
    flattened = [
        Quad(quad.subject, quad.predicate, quad.object, DefaultGraph())
        for quad in quads
        if not isinstance(quad.subject, Triple) and not isinstance(quad.object, Triple)
    ]
    graph = RdflibGraph()
    if not flattened:
        return graph

    payload = serialize(flattened, format=RdfFormat.N_TRIPLES)
    text = payload.decode("utf-8") if isinstance(payload, bytes) else str(payload)
    graph.parse(data=text, format="nt")
    return graph


def from_rdflib(graph: RdflibGraph, target: GraphName) -> list[Quad]:
    """Bring an rdflib graph back as quads in ``target``."""
    text = _serialise(graph)
    if not text:
        return []
    return [
        Quad(item.subject, item.predicate, item.object, target)
        for item in parse(text, format=RdfFormat.N_TRIPLES)
    ]


def triples_from_rdflib(graph: RdflibGraph) -> set[Triple]:
    """The same, as bare triples, for callers that place them themselves."""
    text = _serialise(graph)
    if not text:
        return set()
    return {
        Triple(item.subject, item.predicate, item.object)
        for item in parse(text, format=RdfFormat.N_TRIPLES)
    }


def _serialise(graph: RdflibGraph) -> str:
    """N-Triples for the part of ``graph`` that is well-formed RDF.

    rdflib stores generalised triples happily -- a literal in the subject slot,
    say -- and owlrl does produce some while chasing ``owl:sameAs``. RDF does not
    allow them and pyoxigraph rightly refuses to parse them, so they are dropped
    here rather than being allowed to fail the whole closure.
    """
    if len(graph) == 0:
        return ""

    usable = RdflibGraph()
    for subject, predicate, obj in graph:
        if not isinstance(subject, RdflibURIRef | RdflibBNode):
            continue
        if not isinstance(predicate, RdflibURIRef):
            continue
        usable.add((subject, predicate, obj))

    if len(usable) == 0:
        return ""
    return str(usable.serialize(format="nt"))
