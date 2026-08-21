"""What OWL 2 RL derives that the earlier hand-written rules could not (§5.3, §10.1)."""

from __future__ import annotations

import pytest
from pyoxigraph import NamedNode, RdfFormat, Triple, parse

from ontoforge.reasoning.closure import owl_closure
from ontoforge.reasoning.rules import Profile

ONT = "https://example.org/kg/ont#"
ID = "https://example.org/kg/id/"

PREFIXES = """
@prefix ont: <https://example.org/kg/ont#> .
@prefix id:  <https://example.org/kg/id/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
"""


def n(suffix: str, *, base: str = ONT) -> NamedNode:
    return NamedNode(f"{base}{suffix}")


def t(subject: str, predicate: str, obj: str) -> Triple:
    namespaces = {
        "ont": ONT,
        "id": ID,
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "owl": "http://www.w3.org/2002/07/owl#",
    }

    def resolve(term: str) -> NamedNode:
        prefix, _, local = term.partition(":")
        return NamedNode(namespaces[prefix] + local)

    return Triple(resolve(subject), resolve(predicate), resolve(obj))


RDF_TYPE = NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")


def derive(turtle: str, profile: Profile = Profile.OWL2_RL) -> set[Triple]:
    quads = list(parse(PREFIXES + turtle, format=RdfFormat.TURTLE))
    return owl_closure(quads, profile=profile)


# ---------------------------------------------------------------- what RDFS already did


def test_a_subclass_still_gives_its_instances_the_parent_type() -> None:
    derived = derive(
        "ont:Employee rdfs:subClassOf ont:Person . id:alice a ont:Employee .",
        Profile.RDFS,
    )
    assert Triple(n("alice", base=ID), RDF_TYPE, n("Person")) in derived


def test_a_domain_still_types_the_subject() -> None:
    derived = derive(
        "ont:worksFor rdfs:domain ont:Person . id:alice ont:worksFor id:acme .", Profile.RDFS
    )
    assert Triple(n("alice", base=ID), RDF_TYPE, n("Person")) in derived


def test_an_inverse_property_is_filled_in() -> None:
    derived = derive("ont:worksFor owl:inverseOf ont:employs . id:alice ont:worksFor id:acme .")
    assert t("id:acme", "ont:employs", "id:alice") in derived


def test_a_transitive_property_is_followed() -> None:
    derived = derive(
        "ont:partOf a owl:TransitiveProperty . id:a ont:partOf id:b . id:b ont:partOf id:c ."
    )
    assert t("id:a", "ont:partOf", "id:c") in derived


def test_the_none_profile_derives_nothing() -> None:
    assert derive("ont:Employee rdfs:subClassOf ont:Person .", Profile.NONE) == set()


# ---------------------------------------------------------------- what only OWL 2 RL does


def test_a_property_chain_reaches_through_the_parent_organisation() -> None:
    # 「田中太郎はアクメ東京支社に所属」＋「東京支社はアクメの一部」
    #  → 「田中太郎はアクメにも所属」
    derived = derive(
        """
        ont:worksFor owl:propertyChainAxiom ( ont:worksFor ont:partOf ) .
        id:alice ont:worksFor id:acmeTokyo .
        id:acmeTokyo ont:partOf id:acme .
        """
    )
    assert t("id:alice", "ont:worksFor", "id:acme") in derived


def test_a_defined_class_classifies_by_some_values_from() -> None:
    derived = derive(
        """
        ont:Employed owl:equivalentClass [ a owl:Restriction ;
            owl:onProperty ont:worksFor ; owl:someValuesFrom ont:Organization ] .
        id:alice ont:worksFor id:acme .
        id:acme a ont:Organization .
        """
    )
    assert Triple(n("alice", base=ID), RDF_TYPE, n("Employed")) in derived


def test_a_defined_class_classifies_by_has_value() -> None:
    derived = derive(
        """
        ont:TokyoWorker owl:equivalentClass [ a owl:Restriction ;
            owl:onProperty ont:city ; owl:hasValue id:tokyo ] .
        id:alice ont:city id:tokyo .
        """
    )
    assert Triple(n("alice", base=ID), RDF_TYPE, n("TokyoWorker")) in derived


def test_a_defined_class_classifies_by_intersection() -> None:
    derived = derive(
        """
        ont:SeniorEmployee owl:equivalentClass [ owl:intersectionOf ( ont:Employee ont:Senior ) ] .
        id:alice a ont:Employee , ont:Senior .
        """
    )
    assert Triple(n("alice", base=ID), RDF_TYPE, n("SeniorEmployee")) in derived


def test_rdfs_alone_does_not_reach_the_owl_constructs() -> None:
    turtle = """
    ont:worksFor owl:propertyChainAxiom ( ont:worksFor ont:partOf ) .
    id:alice ont:worksFor id:acmeTokyo .
    id:acmeTokyo ont:partOf id:acme .
    """
    assert t("id:alice", "ont:worksFor", "id:acme") not in derive(turtle, Profile.RDFS)


# ---------------------------------------------------------------- shape of the result


def test_only_new_triples_come_back() -> None:
    turtle = "ont:Employee rdfs:subClassOf ont:Person . id:alice a ont:Employee ."
    derived = derive(turtle)
    assert Triple(n("alice", base=ID), RDF_TYPE, n("Employee")) not in derived
    assert t("ont:Employee", "rdfs:subClassOf", "ont:Person") not in derived


def test_an_empty_graph_derives_nothing_of_its_own() -> None:
    assert derive("") == set()


def test_the_closure_is_deterministic() -> None:
    turtle = "ont:Employee rdfs:subClassOf ont:Person . id:alice a ont:Employee ."
    assert derive(turtle) == derive(turtle)


@pytest.mark.parametrize("profile", [Profile.RDFS, Profile.RL_LITE, Profile.OWL2_RL])
def test_every_profile_runs(profile: Profile) -> None:
    assert isinstance(derive("id:alice a ont:Person .", profile), set)
