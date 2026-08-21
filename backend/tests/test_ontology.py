from __future__ import annotations

import pytest

from ontoforge.entities import EntityService
from ontoforge.namespaces import OWL_CLASS, OWL_OBJECT_PROPERTY, RDFS_SUBCLASS_OF
from ontoforge.ontology import OntologyService, TermNotFoundError
from ontoforge.runtime import Runtime
from ontoforge.store import graphs

ONT = "https://example.org/kg/ont#"


@pytest.fixture
def service(runtime: Runtime) -> OntologyService:
    return OntologyService(runtime)


def test_a_class_gets_a_readable_iri_from_its_label(service: OntologyService) -> None:
    created = service.add_class(label="business unit")
    assert created["@id"] == f"{ONT}BusinessUnit"
    assert created["@type"] == [OWL_CLASS.value]


def test_a_property_gets_a_camel_case_iri(service: OntologyService) -> None:
    created = service.add_property(label="works for")
    assert created["@id"] == f"{ONT}worksFor"
    assert created["@type"] == [OWL_OBJECT_PROPERTY.value]


def test_definitions_land_in_the_ontology_graph(service: OntologyService, runtime: Runtime) -> None:
    service.add_class(label="人物")
    assert runtime.store.count(graphs.ONTOLOGY) > 0
    assert runtime.store.count(graphs.DATA) == 0


def test_a_datatype_property_is_typed_as_such(service: OntologyService) -> None:
    created = service.add_property(label="founded year", kind="datatype")
    assert created["@type"] == ["http://www.w3.org/2002/07/owl#DatatypeProperty"]


def test_a_subclass_records_its_parent(service: OntologyService, runtime: Runtime) -> None:
    service.add_class(label="人物")
    child = service.add_class(label="社員", parents=[f"{ONT}人物"])
    assert child[RDFS_SUBCLASS_OF.value] == [{"@id": f"{ONT}人物"}]


def test_the_tree_nests_subclasses_under_their_parent(service: OntologyService) -> None:
    service.add_class(label="人物")
    service.add_class(label="社員", parents=["ont:人物"])
    (root,) = service.tree()["classes"]
    assert root["iri"] == f"{ONT}人物"
    assert [child["iri"] for child in root["children"]] == [f"{ONT}社員"]


def test_the_tree_reports_how_many_instances_each_class_has(
    service: OntologyService, runtime: Runtime
) -> None:
    service.add_class(label="人物")
    EntityService(runtime).create(label="田中太郎", types=[f"{ONT}人物"])
    (root,) = service.tree()["classes"]
    assert root["instanceCount"] == 1


def test_properties_report_their_domain_and_range(service: OntologyService) -> None:
    service.add_class(label="人物")
    service.add_class(label="組織")
    service.add_property(label="所属", domain=f"{ONT}人物", range_=f"{ONT}組織")
    (prop,) = service.tree()["properties"]
    assert prop["domain"] == [f"{ONT}人物"]
    assert prop["range"] == [f"{ONT}組織"]


def test_a_cycle_in_the_hierarchy_does_not_hang_the_tree(service: OntologyService) -> None:
    service.add_class(label="a")
    service.add_class(label="b", parents=[f"{ONT}A"])
    service.add_class(label="a", parents=[f"{ONT}B"])
    assert service.tree()["classes"] is not None


def test_a_duplicate_label_reuses_the_same_term(service: OntologyService) -> None:
    first = service.add_class(label="人物")
    second = service.add_class(label="人物", comment="ふたたび")
    assert first["@id"] == second["@id"]


def test_candidate_properties_are_filtered_by_domain(service: OntologyService) -> None:
    service.add_class(label="人物")
    service.add_class(label="組織")
    service.add_property(label="所属", domain=f"{ONT}人物", range_=f"{ONT}組織")
    service.add_property(label="設立年", kind="datatype", domain=f"{ONT}組織")
    assert [p["iri"] for p in service.candidate_properties(domain=f"{ONT}人物")] == [f"{ONT}所属"]


def test_a_property_without_a_domain_is_always_a_candidate(service: OntologyService) -> None:
    service.add_class(label="人物")
    service.add_property(label="備考", kind="datatype")
    assert [p["iri"] for p in service.candidate_properties(domain=f"{ONT}人物")] == [f"{ONT}備考"]


def test_renaming_a_term_rewrites_every_reference(
    service: OntologyService, runtime: Runtime
) -> None:
    service.add_class(label="人物")
    entities = EntityService(runtime)
    node = entities.create(label="田中太郎", types=[f"{ONT}人物"])
    renamed = service.rename(f"{ONT}人物", "Person")
    assert renamed["@id"] == f"{ONT}Person"
    assert entities.get(node["@id"])["@type"] == [f"{ONT}Person"]
    assert service.tree()["classes"][0]["iri"] == f"{ONT}Person"


def test_renaming_an_unknown_term_raises(service: OntologyService) -> None:
    with pytest.raises(TermNotFoundError):
        service.rename(f"{ONT}Nope", "Other")


def test_a_class_without_a_label_is_rejected(service: OntologyService) -> None:
    with pytest.raises(ValueError, match="label"):
        service.add_class(label="  ")


def test_ontology_writes_are_recorded_with_the_user_actor(
    service: OntologyService, runtime: Runtime
) -> None:
    service.add_class(label="人物")
    assert runtime.changelog.read_all()[0].actor == "user"
