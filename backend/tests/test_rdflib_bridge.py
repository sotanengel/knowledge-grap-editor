"""The bridge SHACL and the reasoner both cross to reach rdflib."""

from __future__ import annotations

from pyoxigraph import DefaultGraph, Literal, NamedNode, Quad, Triple

from ontoforge.namespaces import RDF_REIFIES, RDFS_LABEL
from ontoforge.rdflib_bridge import from_rdflib, to_rdflib
from ontoforge.store import graphs

ALICE = NamedNode("https://example.org/kg/id/alice")
ACME = NamedNode("https://example.org/kg/id/acme")
WORKS_FOR = NamedNode("https://example.org/kg/ont#worksFor")


def test_quads_cross_to_rdflib_and_back() -> None:
    quads = [
        Quad(ALICE, RDFS_LABEL, Literal("田中太郎", language="ja"), graphs.DATA),
        Quad(ALICE, WORKS_FOR, ACME, graphs.DATA),
    ]
    returned = from_rdflib(to_rdflib(quads), graphs.DATA)
    assert set(returned) == set(quads)


def test_the_target_graph_is_applied_on_the_way_back() -> None:
    quads = [Quad(ALICE, WORKS_FOR, ACME, graphs.DATA)]
    (returned,) = from_rdflib(to_rdflib(quads), graphs.INFERRED)
    assert returned.graph_name == graphs.INFERRED


def test_graph_names_are_flattened_on_the_way_out() -> None:
    # rdflib is handed one graph, so quads from several named graphs merge.
    quads = [
        Quad(ALICE, RDFS_LABEL, Literal("a"), graphs.DATA),
        Quad(ACME, RDFS_LABEL, Literal("b"), graphs.ONTOLOGY),
    ]
    assert len(to_rdflib(quads)) == 2


def test_triple_terms_are_left_behind_because_rdflib_cannot_read_them() -> None:
    reifier = NamedNode("urn:ontoforge:derivation/1")
    edge = Triple(ALICE, WORKS_FOR, ACME)
    quads = [
        Quad(ALICE, WORKS_FOR, ACME, graphs.DATA),
        Quad(reifier, RDF_REIFIES, edge, graphs.INFERRED),
    ]
    assert len(to_rdflib(quads)) == 1


def test_an_empty_input_gives_an_empty_graph() -> None:
    assert len(to_rdflib([])) == 0
    assert from_rdflib(to_rdflib([]), graphs.DATA) == []


def test_the_default_graph_is_accepted_on_the_way_back() -> None:
    quads = [Quad(ALICE, WORKS_FOR, ACME, graphs.DATA)]
    (returned,) = from_rdflib(to_rdflib(quads), DefaultGraph())
    assert isinstance(returned.graph_name, DefaultGraph)


def test_a_generalised_triple_is_dropped_rather_than_breaking_the_crossing() -> None:
    """rdflib tolerates a literal in the subject slot; RDF does not.

    owlrl produces some while chasing `owl:sameAs`, and letting one through would
    fail the whole closure with a parse error.
    """
    from rdflib import Graph as RdflibGraph
    from rdflib import Literal as RdflibLiteral
    from rdflib import URIRef

    graph = RdflibGraph()
    graph.add((URIRef("https://a"), URIRef("https://p"), URIRef("https://b")))
    graph.add((RdflibLiteral("not a subject"), URIRef("https://p"), URIRef("https://b")))

    quads = from_rdflib(graph, graphs.DATA)
    assert len(quads) == 1
    assert quads[0].subject == NamedNode("https://a")


def test_a_graph_of_nothing_but_generalised_triples_comes_back_empty() -> None:
    from rdflib import Graph as RdflibGraph
    from rdflib import Literal as RdflibLiteral
    from rdflib import URIRef

    graph = RdflibGraph()
    graph.add((RdflibLiteral("x"), URIRef("https://p"), URIRef("https://b")))
    assert from_rdflib(graph, graphs.DATA) == []
