"""Recovering *why* a triple was derived, when the reasoner will not say (§10.1)."""

from __future__ import annotations

from pyoxigraph import NamedNode, RdfFormat, Triple, parse

from ontoforge.reasoning.justify import Justification, justify, name_step
from ontoforge.reasoning.rules import Profile

ONT = "https://example.org/kg/ont#"
ID = "https://example.org/kg/id/"
RDF_TYPE = NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

SOURCE = """
@prefix ont: <https://example.org/kg/ont#> .
@prefix id:  <https://example.org/kg/id/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ont:Employee rdfs:subClassOf ont:Person .
ont:Person rdfs:subClassOf ont:Agent .
ont:worksFor rdfs:domain ont:Person ; owl:inverseOf ont:employs .
ont:partOf a owl:TransitiveProperty .
ont:worksFor owl:propertyChainAxiom ( ont:worksFor ont:partOf ) .

id:alice a ont:Employee ; ont:worksFor id:acmeTokyo .
id:acmeTokyo ont:partOf id:acme .
id:bob a ont:Employee .
id:carol ont:worksFor id:other .
id:dave a ont:Employee .
"""


def candidates() -> list[Triple]:
    return [
        Triple(quad.subject, quad.predicate, quad.object)
        for quad in parse(SOURCE, format=RdfFormat.TURTLE)
    ]


def entails(premises, conclusion) -> bool:
    from ontoforge.reasoning.closure import entails as check

    return check(premises, conclusion, profile=Profile.OWL2_RL)


def n(local: str, *, base: str = ONT) -> NamedNode:
    return NamedNode(base + local)


ALICE_IS_A_PERSON = Triple(n("alice", base=ID), RDF_TYPE, n("Person"))
ALICE_WORKS_FOR_ACME = Triple(n("alice", base=ID), n("worksFor"), n("acme", base=ID))


# ---------------------------------------------------------------- finding a reason


def test_a_derived_type_gets_its_premises_back() -> None:
    # There are two ways to reach this one: through `Employee subClassOf Person`
    # and through `worksFor rdfs:domain Person`. Either is a correct answer, so
    # what is asserted is that the premises really do entail the conclusion --
    # `test_the_answer_is_minimal...` covers the other half.
    found = justify(ALICE_IS_A_PERSON, candidates(), entails)
    assert found is not None
    assert found.premises
    assert entails(found.premises, ALICE_IS_A_PERSON)
    assert Triple(n("alice", base=ID), RDF_TYPE, n("Person")) not in found.premises


def test_the_step_is_named_when_one_of_our_rules_accounts_for_it() -> None:
    found = justify(ALICE_IS_A_PERSON, candidates(), entails)
    assert found is not None
    assert found.rule in {"rdfs:subClassOf-type", "rdfs:domain"}


def test_a_property_chain_derivation_gets_both_of_its_steps_back() -> None:
    found = justify(ALICE_WORKS_FOR_ACME, candidates(), entails)
    assert found is not None
    facts = set(found.premises)
    assert Triple(n("alice", base=ID), n("worksFor"), n("acmeTokyo", base=ID)) in facts
    assert Triple(n("acmeTokyo", base=ID), n("partOf"), n("acme", base=ID)) in facts


# ---------------------------------------------------------------- minimality


def test_the_answer_is_minimal_so_every_premise_is_load_bearing() -> None:
    found = justify(ALICE_IS_A_PERSON, candidates(), entails)
    assert found is not None
    for premise in found.premises:
        without = [item for item in found.premises if item != premise]
        assert not entails(without, ALICE_IS_A_PERSON), f"{premise} was not needed"


def test_unrelated_facts_are_left_out() -> None:
    found = justify(ALICE_IS_A_PERSON, candidates(), entails)
    assert found is not None
    assert Triple(n("bob", base=ID), RDF_TYPE, n("Employee")) not in found.premises
    assert Triple(n("dave", base=ID), RDF_TYPE, n("Employee")) not in found.premises


# ---------------------------------------------------------------- honesty


def test_something_the_candidates_cannot_account_for_returns_nothing() -> None:
    outside = Triple(n("zoe", base=ID), RDF_TYPE, n("Person"))
    assert justify(outside, candidates(), entails) is None


def test_an_asserted_triple_needs_only_itself() -> None:
    asserted = Triple(n("alice", base=ID), RDF_TYPE, n("Employee"))
    found = justify(asserted, candidates(), entails)
    assert found is not None
    assert found.premises == [asserted]


def test_no_candidates_means_no_justification() -> None:
    assert justify(ALICE_IS_A_PERSON, [], entails) is None


# ---------------------------------------------------------------- cost


def test_the_search_splits_rather_than_walking_one_at_a_time() -> None:
    """QuickXplain runs the closure O(log n) times, not O(n)."""
    calls = 0

    def counting(premises, conclusion) -> bool:
        nonlocal calls
        calls += 1
        return entails(premises, conclusion)

    padding = [Triple(n(f"pad{index}", base=ID), RDF_TYPE, n("Employee")) for index in range(60)]
    found = justify(ALICE_IS_A_PERSON, [*candidates(), *padding], counting)
    assert found is not None
    # Dropping one at a time over ~75 candidates would be ~75 closure runs.
    assert calls < 40, f"took {calls} closure runs"


# ---------------------------------------------------------------- naming the step


def test_a_step_a_known_rule_accounts_for_is_named() -> None:
    premises = [
        Triple(n("alice", base=ID), RDF_TYPE, n("Employee")),
        Triple(
            n("Employee"), NamedNode("http://www.w3.org/2000/01/rdf-schema#subClassOf"), n("Person")
        ),
    ]
    assert name_step(ALICE_IS_A_PERSON, premises, profile=Profile.RDFS) == "rdfs:subClassOf-type"


def test_a_step_no_rule_accounts_for_says_so_rather_than_guessing() -> None:
    premises = [
        Triple(n("alice", base=ID), n("worksFor"), n("acmeTokyo", base=ID)),
        Triple(n("acmeTokyo", base=ID), n("partOf"), n("acme", base=ID)),
    ]
    named = name_step(ALICE_WORKS_FOR_ACME, premises, profile=Profile.OWL2_RL)
    assert named == "OWL 2 RL closure"


def test_a_justification_reports_which_profile_produced_it() -> None:
    found = justify(ALICE_IS_A_PERSON, candidates(), entails)
    assert isinstance(found, Justification)
    assert found.premises
