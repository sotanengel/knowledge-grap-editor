from __future__ import annotations

import pytest
from pyoxigraph import NamedNode, Quad, Triple

from ontoforge.namespaces import OWL, RDF_TYPE, RDFS_DOMAIN, RDFS_RANGE, RDFS_SUBCLASS_OF
from ontoforge.reasoning.engine import materialise
from ontoforge.reasoning.rules import Profile, describe_profile, rules_for
from ontoforge.reasoning.service import ReasonerService
from ontoforge.runtime import Runtime
from ontoforge.store import graphs

ONT = "https://example.org/kg/ont#"
ID = "https://example.org/kg/id/"

PERSON = NamedNode(f"{ONT}Person")
EMPLOYEE = NamedNode(f"{ONT}Employee")
AGENT = NamedNode(f"{ONT}Agent")
ORGANIZATION = NamedNode(f"{ONT}Organization")
WORKS_FOR = NamedNode(f"{ONT}worksFor")
EMPLOYS = NamedNode(f"{ONT}employs")
PART_OF = NamedNode(f"{ONT}partOf")
KNOWS = NamedNode(f"{ONT}knows")

ALICE = NamedNode(f"{ID}alice")
ACME = NamedNode(f"{ID}acme")
BOB = NamedNode(f"{ID}bob")

SUBCLASS = RDFS_SUBCLASS_OF
TRANSITIVE = NamedNode(f"{OWL}TransitiveProperty")
SYMMETRIC = NamedNode(f"{OWL}SymmetricProperty")
INVERSE_OF = NamedNode(f"{OWL}inverseOf")
EQUIVALENT_CLASS = NamedNode(f"{OWL}equivalentClass")
SAME_AS = NamedNode(f"{OWL}sameAs")


def t(s: NamedNode, p: NamedNode, o: NamedNode) -> Triple:
    return Triple(s, p, o)


def derived(facts: list[Triple], profile: Profile = Profile.RDFS) -> set[Triple]:
    return set(materialise(facts, profile=profile).triples)


# ---------------------------------------------------------------- profiles


def test_the_none_profile_derives_nothing() -> None:
    assert derived([t(EMPLOYEE, SUBCLASS, PERSON)], Profile.NONE) == set()
    assert rules_for(Profile.NONE) == ()


def test_rl_lite_is_a_superset_of_rdfs() -> None:
    assert set(rules_for(Profile.RDFS)) < set(rules_for(Profile.RL_LITE))


def test_each_rule_carries_a_plain_language_description() -> None:
    assert all(entry["description"] for entry in describe_profile(Profile.RL_LITE))


# ---------------------------------------------------------------- rdfs


def test_subclass_is_transitive() -> None:
    facts = [t(EMPLOYEE, SUBCLASS, PERSON), t(PERSON, SUBCLASS, AGENT)]
    assert t(EMPLOYEE, SUBCLASS, AGENT) in derived(facts)


def test_an_instance_inherits_its_parent_class() -> None:
    facts = [t(EMPLOYEE, SUBCLASS, PERSON), t(ALICE, RDF_TYPE, EMPLOYEE)]
    assert t(ALICE, RDF_TYPE, PERSON) in derived(facts)


def test_a_domain_gives_the_subject_a_type() -> None:
    facts = [t(WORKS_FOR, RDFS_DOMAIN, PERSON), t(ALICE, WORKS_FOR, ACME)]
    assert t(ALICE, RDF_TYPE, PERSON) in derived(facts)


def test_a_range_gives_the_object_a_type() -> None:
    facts = [t(WORKS_FOR, RDFS_RANGE, ORGANIZATION), t(ALICE, WORKS_FOR, ACME)]
    assert t(ACME, RDF_TYPE, ORGANIZATION) in derived(facts)


def test_rdfs_alone_does_not_reach_for_owl_rules() -> None:
    facts = [t(WORKS_FOR, INVERSE_OF, EMPLOYS), t(ALICE, WORKS_FOR, ACME)]
    assert t(ACME, EMPLOYS, ALICE) not in derived(facts, Profile.RDFS)


# ---------------------------------------------------------------- rl-lite


def test_an_inverse_property_fills_in_the_other_direction() -> None:
    facts = [t(WORKS_FOR, INVERSE_OF, EMPLOYS), t(ALICE, WORKS_FOR, ACME)]
    assert t(ACME, EMPLOYS, ALICE) in derived(facts, Profile.RL_LITE)


def test_a_transitive_property_is_followed() -> None:
    part = NamedNode(f"{ID}part")
    whole = NamedNode(f"{ID}whole")
    middle = NamedNode(f"{ID}middle")
    facts = [
        t(PART_OF, RDF_TYPE, TRANSITIVE),
        t(part, PART_OF, middle),
        t(middle, PART_OF, whole),
    ]
    assert t(part, PART_OF, whole) in derived(facts, Profile.RL_LITE)


def test_a_symmetric_property_holds_both_ways() -> None:
    facts = [t(KNOWS, RDF_TYPE, SYMMETRIC), t(ALICE, KNOWS, BOB)]
    assert t(BOB, KNOWS, ALICE) in derived(facts, Profile.RL_LITE)


def test_equivalent_classes_become_mutual_subclasses() -> None:
    facts = [t(PERSON, EQUIVALENT_CLASS, AGENT)]
    result = derived(facts, Profile.RL_LITE)
    assert t(PERSON, SUBCLASS, AGENT) in result
    assert t(AGENT, SUBCLASS, PERSON) in result


def test_same_as_propagates_statements_in_both_positions() -> None:
    facts = [t(ALICE, SAME_AS, BOB), t(ALICE, WORKS_FOR, ACME)]
    result = derived(facts, Profile.RL_LITE)
    assert t(BOB, SAME_AS, ALICE) in result
    assert t(BOB, WORKS_FOR, ACME) in result


# ---------------------------------------------------------------- termination


def test_a_cyclic_hierarchy_still_terminates() -> None:
    facts = [t(PERSON, SUBCLASS, AGENT), t(AGENT, SUBCLASS, PERSON), t(ALICE, RDF_TYPE, PERSON)]
    result = materialise(facts, profile=Profile.RL_LITE)
    assert result.reached_fixed_point
    assert t(ALICE, RDF_TYPE, AGENT) in set(result.triples)


def test_the_iteration_cap_is_honoured() -> None:
    chain = [NamedNode(f"{ONT}C{n}") for n in range(30)]
    facts = [t(chain[n], SUBCLASS, chain[n + 1]) for n in range(29)]
    result = materialise(facts, profile=Profile.RDFS, max_iterations=2)
    assert result.iterations == 2
    assert not result.reached_fixed_point


def test_the_derivation_cap_is_honoured() -> None:
    chain = [NamedNode(f"{ONT}C{n}") for n in range(20)]
    facts = [t(chain[n], SUBCLASS, chain[n + 1]) for n in range(19)]
    result = materialise(facts, profile=Profile.RDFS, max_derivations=5)
    assert result.hit_derivation_cap
    assert result.count == 5


def test_nothing_is_re_derived_that_was_already_asserted() -> None:
    facts = [
        t(EMPLOYEE, SUBCLASS, PERSON),
        t(ALICE, RDF_TYPE, EMPLOYEE),
        t(ALICE, RDF_TYPE, PERSON),
    ]
    assert t(ALICE, RDF_TYPE, PERSON) not in derived(facts)


def test_a_rule_that_would_put_a_literal_in_the_subject_slot_does_not_fire() -> None:
    from pyoxigraph import Literal

    facts = [
        Triple(WORKS_FOR, RDFS_RANGE, ORGANIZATION),
        Triple(ALICE, WORKS_FOR, Literal("acme")),
        Triple(KNOWS, RDF_TYPE, SYMMETRIC),
        Triple(ALICE, KNOWS, Literal("bob")),
    ]
    result = materialise(facts, profile=Profile.RL_LITE)
    assert all(not isinstance(triple.subject, Literal) for triple in result.triples)


# ---------------------------------------------------------------- explanation


def test_every_derivation_records_its_rule_and_premises() -> None:
    facts = [t(EMPLOYEE, SUBCLASS, PERSON), t(ALICE, RDF_TYPE, EMPLOYEE)]
    (derivation,) = [
        d for d in materialise(facts).derivations if d.triple == t(ALICE, RDF_TYPE, PERSON)
    ]
    assert derivation.rule == "rdfs:subClassOf-type"
    assert set(derivation.premises) == set(facts)


# ---------------------------------------------------------------- service


@pytest.fixture
def service(runtime: Runtime) -> ReasonerService:
    runtime.write(
        additions=[
            Quad(EMPLOYEE, SUBCLASS, PERSON, graphs.ONTOLOGY),
            Quad(ALICE, RDF_TYPE, EMPLOYEE, graphs.DATA),
        ]
    )
    return ReasonerService(runtime)


def test_running_the_reasoner_fills_the_inferred_graph(
    service: ReasonerService, runtime: Runtime
) -> None:
    summary = service.run()
    assert summary.derived == 1
    assert summary.profile == "rdfs"
    assert runtime.store.count(graphs.INFERRED) > 0


def test_derived_triples_stay_out_of_the_authored_graphs(
    service: ReasonerService, runtime: Runtime
) -> None:
    service.run()
    assert runtime.store.count(graphs.DATA) == 1
    assert service.derived_triples() == [t(ALICE, RDF_TYPE, PERSON)]


def test_the_inferred_graph_is_rebuilt_not_appended_to(
    service: ReasonerService, runtime: Runtime
) -> None:
    service.run()
    first = runtime.store.count(graphs.INFERRED)
    service.run()
    assert runtime.store.count(graphs.INFERRED) == first


def test_clearing_empties_the_inferred_graph(service: ReasonerService, runtime: Runtime) -> None:
    service.run()
    service.clear()
    assert runtime.store.count(graphs.INFERRED) == 0


def test_the_reasoner_is_recorded_as_the_actor(service: ReasonerService, runtime: Runtime) -> None:
    service.run()
    assert runtime.changelog.read_all()[-1].actor == "reasoner"


def test_an_explanation_names_the_rule_and_its_premises(service: ReasonerService) -> None:
    service.run()
    explanation = service.explain(t(ALICE, RDF_TYPE, PERSON))
    assert explanation is not None
    assert explanation.rule == "rdfs:subClassOf-type"
    assert len(explanation.premises) == 2
    assert "Person" in explanation.triple["text"]


def test_explaining_something_that_was_not_derived_returns_nothing(
    service: ReasonerService,
) -> None:
    service.run()
    assert service.explain(t(ALICE, RDF_TYPE, ORGANIZATION)) is None


def test_the_profile_can_be_overridden_per_run(service: ReasonerService, runtime: Runtime) -> None:
    runtime.write(
        additions=[
            Quad(WORKS_FOR, INVERSE_OF, EMPLOYS, graphs.ONTOLOGY),
            Quad(ALICE, WORKS_FOR, ACME, graphs.DATA),
        ]
    )
    service.run(profile="rdfs")
    assert t(ACME, EMPLOYS, ALICE) not in service.derived_triples()
    service.run(profile="rl-lite")
    assert t(ACME, EMPLOYS, ALICE) in service.derived_triples()


def test_the_none_profile_leaves_the_inferred_graph_empty(
    service: ReasonerService, runtime: Runtime
) -> None:
    service.run()
    service.run(profile="none")
    assert runtime.store.count(graphs.INFERRED) == 0
