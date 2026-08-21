"""Edge metadata via RDF 1.2 triple terms (§6.3).

Provenance, confidence and assertion time hang off the edge itself rather than
being reified into four extra triples, which keeps the graph as direct to read
as a property graph::

    :alice :worksFor :acme ~ :stmt/9f3c .

    :stmt/9f3c rdf:reifies <<( :alice :worksFor :acme )>> ;
        prov:wasDerivedFrom <https://example.com/source/123> ;
        ontf:confidence 0.85 .

In RDF 1.2 a triple term may only appear as an object, so the annotations hang
off a *reifier* node. Its IRI is derived from the edge, which makes re-asserting
the same metadata idempotent instead of piling up duplicates.

Because AI clients never write, the main use is recording where imported data
came from, plus a confidence note when a person enters something by hand.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from pyoxigraph import Literal, NamedNode, Quad, Triple

from ontoforge.literals import XSD_DATETIME, XSD_DECIMAL
from ontoforge.namespaces import (
    ONTF_ASSERTED_AT,
    ONTF_ASSERTED_BY,
    ONTF_CONFIDENCE,
    PROV_WAS_DERIVED_FROM,
    RDF_REIFIES,
)
from ontoforge.store import graphs
from ontoforge.store.store import GraphStore

REIFIER_SUFFIX = "stmt/"
_HASH_LENGTH = 26


@dataclass(frozen=True, slots=True)
class EdgeMetadata:
    """What is known about how an edge came to be asserted."""

    source: str | None = None
    confidence: float | None = None
    asserted_at: str | None = None
    asserted_by: str | None = None

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    @property
    def is_empty(self) -> bool:
        return not any((self.source, self.confidence, self.asserted_at, self.asserted_by))


def reifier_for(edge: Triple, base_iri: str) -> NamedNode:
    """The stable node that carries ``edge``'s annotations."""
    digest = hashlib.sha256(str(edge).encode("utf-8")).hexdigest()[:_HASH_LENGTH]
    return NamedNode(f"{base_iri}{REIFIER_SUFFIX}{digest}")


def edge_metadata_quads(
    edge: Triple,
    metadata: EdgeMetadata,
    *,
    graph: NamedNode = graphs.DATA,
    base_iri: str = "https://example.org/kg/",
) -> list[Quad]:
    """The quads that record ``metadata`` about ``edge``. Empty metadata writes nothing."""
    if metadata.is_empty:
        return []

    reifier = reifier_for(edge, base_iri)
    quads = [Quad(reifier, RDF_REIFIES, edge, graph)]
    if metadata.source:
        quads.append(Quad(reifier, PROV_WAS_DERIVED_FROM, NamedNode(metadata.source), graph))
    if metadata.confidence is not None:
        quads.append(
            Quad(
                reifier,
                ONTF_CONFIDENCE,
                Literal(repr(float(metadata.confidence)), datatype=XSD_DECIMAL),
                graph,
            )
        )
    if metadata.asserted_at:
        quads.append(
            Quad(
                reifier,
                ONTF_ASSERTED_AT,
                Literal(metadata.asserted_at, datatype=XSD_DATETIME),
                graph,
            )
        )
    if metadata.asserted_by:
        quads.append(Quad(reifier, ONTF_ASSERTED_BY, NamedNode(metadata.asserted_by), graph))
    return quads


def reifiers_of(store: GraphStore, edge: Triple) -> list[Any]:
    """Every node that reifies ``edge``, whatever minted it."""
    return [quad.subject for quad in store.quads_for_pattern(None, RDF_REIFIES, edge, None)]


def read_edge_metadata(store: GraphStore, edge: Triple) -> EdgeMetadata:
    """Read back whatever is recorded about ``edge``; missing fields stay ``None``."""
    found: dict[str, Any] = {}
    for reifier in reifiers_of(store, edge):
        for quad in store.quads_for_pattern(reifier, None, None, None):
            value = quad.object
            if isinstance(value, Triple):
                continue
            if quad.predicate == PROV_WAS_DERIVED_FROM:
                found["source"] = value.value
            elif quad.predicate == ONTF_CONFIDENCE:
                found["confidence"] = float(value.value)
            elif quad.predicate == ONTF_ASSERTED_AT:
                found["asserted_at"] = value.value
            elif quad.predicate == ONTF_ASSERTED_BY:
                found["asserted_by"] = value.value
    return EdgeMetadata(**found)


def replace_edge_metadata(
    store: GraphStore,
    edge: Triple,
    metadata: EdgeMetadata,
    *,
    graph: NamedNode = graphs.DATA,
    base_iri: str = "https://example.org/kg/",
) -> tuple[list[Quad], list[Quad]]:
    """Additions and deletions that make ``edge`` carry exactly ``metadata``."""
    deletions = [
        quad
        for reifier in reifiers_of(store, edge)
        for quad in store.quads_for_pattern(reifier, None, None, None)
    ]
    additions = edge_metadata_quads(edge, metadata, graph=graph, base_iri=base_iri)
    return additions, deletions
