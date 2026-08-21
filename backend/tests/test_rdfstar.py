from __future__ import annotations

import pytest
from pyoxigraph import NamedNode, Quad, Triple

from ontoforge.namespaces import ONTF_CONFIDENCE, PROV_WAS_DERIVED_FROM, RDF_REIFIES
from ontoforge.rdfstar import (
    EdgeMetadata,
    edge_metadata_quads,
    read_edge_metadata,
    reifier_for,
    replace_edge_metadata,
)
from ontoforge.runtime import Runtime
from ontoforge.store import graphs

ALICE = NamedNode("https://example.org/kg/id/alice")
ACME = NamedNode("https://example.org/kg/id/acme")
WORKS_FOR = NamedNode("https://example.org/kg/ont#worksFor")
EDGE = Triple(ALICE, WORKS_FOR, ACME)


def test_metadata_hangs_off_a_reifier_pointing_at_the_triple_term() -> None:
    quads = edge_metadata_quads(
        EDGE,
        EdgeMetadata(source="https://example.com/source/123", confidence=0.85),
        graph=graphs.DATA,
    )
    reifier = reifier_for(EDGE, "https://example.org/kg/")
    assert {quad.subject for quad in quads} == {reifier}
    assert {quad.predicate for quad in quads} == {
        RDF_REIFIES,
        PROV_WAS_DERIVED_FROM,
        ONTF_CONFIDENCE,
    }
    (reifies,) = [quad for quad in quads if quad.predicate == RDF_REIFIES]
    assert reifies.object == EDGE


def test_the_reifier_iri_is_stable_for_the_same_edge() -> None:
    base = "https://example.org/kg/"
    assert reifier_for(EDGE, base) == reifier_for(EDGE, base)
    other = Triple(ACME, WORKS_FOR, ALICE)
    assert reifier_for(other, base) != reifier_for(EDGE, base)


def test_replacing_metadata_clears_what_was_there_before(runtime: Runtime) -> None:
    runtime.write(
        additions=[
            Quad(ALICE, WORKS_FOR, ACME, graphs.DATA),
            *edge_metadata_quads(EDGE, EdgeMetadata(confidence=0.2), graph=graphs.DATA),
        ]
    )
    additions, deletions = replace_edge_metadata(
        runtime.store, EDGE, EdgeMetadata(confidence=0.9), graph=graphs.DATA
    )
    runtime.write(additions=additions, deletions=deletions)
    assert read_edge_metadata(runtime.store, EDGE) == EdgeMetadata(confidence=0.9)


def test_confidence_outside_zero_to_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="confidence"):
        EdgeMetadata(confidence=1.5)


def test_empty_metadata_produces_no_quads() -> None:
    assert edge_metadata_quads(EDGE, EdgeMetadata(), graph=graphs.DATA) == []


def test_metadata_round_trips_through_the_store(runtime: Runtime) -> None:
    original = EdgeMetadata(
        source="https://example.com/source/123",
        confidence=0.85,
        asserted_at="2026-08-20T09:00:00Z",
        asserted_by="https://example.org/kg/user/taro",
    )
    runtime.write(
        additions=[
            Quad(ALICE, WORKS_FOR, ACME, graphs.DATA),
            *edge_metadata_quads(EDGE, original, graph=graphs.DATA),
        ]
    )
    assert read_edge_metadata(runtime.store, EDGE) == original


def test_reading_metadata_for_a_plain_edge_returns_nothing(runtime: Runtime) -> None:
    runtime.write(additions=[Quad(ALICE, WORKS_FOR, ACME, graphs.DATA)])
    assert read_edge_metadata(runtime.store, EDGE) == EdgeMetadata()


def test_quoted_triples_survive_a_turtle_round_trip(runtime: Runtime) -> None:
    runtime.write(
        additions=[
            Quad(ALICE, WORKS_FOR, ACME, graphs.DATA),
            *edge_metadata_quads(EDGE, EdgeMetadata(confidence=0.5), graph=graphs.DATA),
        ]
    )
    turtle = runtime.store.dump_graph(graphs.DATA)
    assert "<<" in turtle or "{|" in turtle
