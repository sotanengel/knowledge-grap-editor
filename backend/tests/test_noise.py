"""What a derived triple has to be before it is worth drawing (§10.1, §7.3-4).

On a small test ontology the OWL 2 RL closure was 185 triples, of which 17 were
about the user's own data and 67 were `x owl:sameAs x`. Everything here is about
telling those apart.
"""

from __future__ import annotations

import pytest
from pyoxigraph import Literal, NamedNode, Triple

from ontoforge.namespaces import (
    OWL,
    RDF_TYPE,
    RDFS,
    RDFS_LABEL,
    RDFS_SUBCLASS_OF,
    RDFS_SUBPROPERTY_OF,
)
from ontoforge.reasoning.noise import (
    NoiseReason,
    is_noise,
    keep_signal,
    noise_reason,
    premise_kind,
)
from ontoforge.store.iri import SKOLEM_SUFFIX

BASE = "https://example.org/kg/"
ONT = f"{BASE}ont#"
ID = f"{BASE}id/"

ALICE = NamedNode(f"{ID}alice")
PERSON = NamedNode(f"{ONT}Person")
EMPLOYEE = NamedNode(f"{ONT}Employee")
WORKS_FOR = NamedNode(f"{ONT}worksFor")
SAME_AS = NamedNode(f"{OWL}sameAs")
EQUIVALENT_CLASS = NamedNode(f"{OWL}equivalentClass")
EQUIVALENT_PROPERTY = NamedNode(f"{OWL}equivalentProperty")
OWL_THING = NamedNode(f"{OWL}Thing")
RDFS_RESOURCE = NamedNode(f"{RDFS}Resource")
SKOLEM = NamedNode(f"{BASE}.well-known/genid/b0")
AGENT = NamedNode(f"{ONT}Agent")
ACME = NamedNode(f"{ID}acme")
OWL_CLASS = NamedNode(f"{OWL}Class")
CHAIN = NamedNode(f"{OWL}propertyChainAxiom")
RDF_FIRST = NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#first")


def t(subject: NamedNode, predicate: NamedNode, obj: NamedNode) -> Triple:
    return Triple(subject, predicate, obj)


def check(triple: Triple) -> bool:
    return is_noise(triple, base_iri=BASE)


# ---------------------------------------------------------------- signal


def test_a_derived_type_about_the_users_data_is_kept() -> None:
    assert not check(Triple(ALICE, RDF_TYPE, PERSON))


def test_a_derived_relation_between_two_items_is_kept() -> None:
    assert not check(Triple(ALICE, WORKS_FOR, NamedNode(f"{ID}acme")))


def test_a_real_subclass_step_is_kept() -> None:
    assert not check(Triple(EMPLOYEE, RDFS_SUBCLASS_OF, PERSON))


def test_a_genuine_identity_between_two_things_is_kept() -> None:
    assert not check(Triple(ALICE, SAME_AS, NamedNode(f"{ID}alice2")))


# ---------------------------------------------------------------- tautologies


@pytest.mark.parametrize(
    "predicate",
    [SAME_AS, RDFS_SUBCLASS_OF, RDFS_SUBPROPERTY_OF, EQUIVALENT_CLASS, EQUIVALENT_PROPERTY],
)
def test_something_related_to_itself_says_nothing(predicate: NamedNode) -> None:
    assert check(Triple(ALICE, predicate, ALICE))
    assert noise_reason(Triple(ALICE, predicate, ALICE), base_iri=BASE) is NoiseReason.TAUTOLOGY


@pytest.mark.parametrize("universal", [OWL_THING, RDFS_RESOURCE])
def test_belonging_to_the_class_of_everything_says_nothing(universal: NamedNode) -> None:
    assert check(Triple(ALICE, RDF_TYPE, universal))
    assert noise_reason(Triple(ALICE, RDF_TYPE, universal), base_iri=BASE) is NoiseReason.UNIVERSAL


@pytest.mark.parametrize(
    "predicate",
    [
        RDFS_SUBCLASS_OF,
        NamedNode(f"{RDFS}domain"),
        NamedNode(f"{RDFS}range"),
    ],
)
def test_a_universal_class_says_nothing_wherever_it_turns_up(predicate: NamedNode) -> None:
    # "Person is a subclass of Thing" and "worksFor has domain Thing" are just as
    # vacuous as "Alice is a Thing", and owlrl derives all three.
    triple = Triple(PERSON, predicate, OWL_THING)
    assert check(triple)
    assert noise_reason(triple, base_iri=BASE) is NoiseReason.UNIVERSAL


def test_a_real_class_in_the_same_position_is_kept() -> None:
    assert not check(Triple(EMPLOYEE, RDFS_SUBCLASS_OF, PERSON))
    assert not check(Triple(WORKS_FOR, NamedNode(f"{RDFS}domain"), PERSON))


# ---------------------------------------------------------------- meta


def test_the_reasoner_talking_about_rdfs_itself_is_not_the_users_business() -> None:
    triple = Triple(NamedNode(f"{RDFS}label"), RDF_TYPE, NamedNode(f"{RDF_TYPE.value}"))
    assert check(triple)
    assert noise_reason(triple, base_iri=BASE) is NoiseReason.VOCABULARY


def test_a_bundled_vocabulary_can_be_added_to_the_exclusion() -> None:
    schema = Triple(NamedNode("https://schema.org/Person"), RDFS_SUBCLASS_OF, PERSON)
    assert not is_noise(schema, base_iri=BASE)
    assert is_noise(schema, base_iri=BASE, vocabulary_namespaces=["https://schema.org/"])


# ---------------------------------------------------------------- constraint internals


def test_a_skolemised_restriction_node_never_reaches_the_canvas() -> None:
    # This is the old defect: `equivalentClass` pointing at a restriction gave
    # `ont:TokyoWorker rdfs:subClassOf <genid>`, drawn as a meaningless edge.
    triple = Triple(NamedNode(f"{ONT}TokyoWorker"), RDFS_SUBCLASS_OF, SKOLEM)
    assert check(triple)
    assert noise_reason(triple, base_iri=BASE) is NoiseReason.CONSTRUCTION


def test_a_skolem_node_is_noise_in_the_subject_position_too() -> None:
    assert check(Triple(SKOLEM, RDFS_SUBCLASS_OF, PERSON))


# ---------------------------------------------------------------- the filter


def test_keep_signal_removes_the_noise_and_reports_what_it_removed() -> None:
    derived = {
        Triple(ALICE, RDF_TYPE, PERSON),
        Triple(ALICE, SAME_AS, ALICE),
        Triple(ALICE, RDF_TYPE, OWL_THING),
        Triple(NamedNode(f"{ONT}TokyoWorker"), RDFS_SUBCLASS_OF, SKOLEM),
    }
    kept, removed = keep_signal(derived, base_iri=BASE)
    assert kept == {Triple(ALICE, RDF_TYPE, PERSON)}
    assert removed[NoiseReason.TAUTOLOGY] == 1
    assert removed[NoiseReason.UNIVERSAL] == 1
    assert removed[NoiseReason.CONSTRUCTION] == 1


def test_keep_signal_leaves_a_clean_set_alone() -> None:
    derived = {Triple(ALICE, RDF_TYPE, PERSON)}
    kept, removed = keep_signal(derived, base_iri=BASE)
    assert kept == derived
    assert sum(removed.values()) == 0


def test_a_literal_object_is_not_mistaken_for_a_node() -> None:
    assert not check(Triple(ALICE, RDFS_LABEL, Literal("田中太郎", language="ja")))


# ---------------------------------------------------------------- premise kinds


def test_a_statement_about_an_individual_is_a_fact() -> None:
    assert premise_kind(t(ALICE, WORKS_FOR, ACME), base_iri=BASE) == "fact"
    assert premise_kind(t(ALICE, RDF_TYPE, PERSON), base_iri=BASE) == "fact"


def test_the_shape_of_a_vocabulary_is_a_definition() -> None:
    assert premise_kind(t(PERSON, RDFS_SUBCLASS_OF, AGENT), base_iri=BASE) == "definition"
    assert premise_kind(t(PERSON, RDF_TYPE, OWL_CLASS), base_iri=BASE) == "definition"


def test_a_skolemised_list_node_is_a_definition() -> None:
    node = NamedNode(f"{BASE}{SKOLEM_SUFFIX}abc123")
    assert premise_kind(t(WORKS_FOR, CHAIN, node), base_iri=BASE) == "definition"
    assert premise_kind(t(node, RDF_FIRST, WORKS_FOR), base_iri=BASE) == "definition"


def test_without_a_base_iri_no_node_is_taken_for_a_skolem() -> None:
    node = NamedNode(f"{BASE}{SKOLEM_SUFFIX}abc123")
    assert premise_kind(t(ALICE, WORKS_FOR, node), base_iri="") == "fact"
