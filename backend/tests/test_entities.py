from __future__ import annotations

import pytest

from ontoforge.entities import EntityNotFoundError, EntityService
from ontoforge.namespaces import RDF_TYPE, RDFS_LABEL
from ontoforge.runtime import Runtime
from ontoforge.store import graphs

PERSON = "https://example.org/kg/ont#Person"
ORGANIZATION = "https://example.org/kg/ont#Organization"
WORKS_FOR = "https://example.org/kg/ont#worksFor"
BIRTH_DATE = "https://example.org/kg/ont#birthDate"


@pytest.fixture
def service(runtime: Runtime) -> EntityService:
    return EntityService(runtime)


def test_create_mints_an_iri_and_returns_a_jsonld_document(service: EntityService) -> None:
    document = service.create(label="田中太郎", types=[PERSON])
    assert document["@id"].startswith("https://example.org/kg/id/")
    assert document["@type"] == [PERSON]
    assert document["@context"]["rdfs"] == "http://www.w3.org/2000/01/rdf-schema#"
    assert document[RDFS_LABEL.value] == [{"@value": "田中太郎", "@language": "ja"}]


def test_labels_default_to_the_japanese_language_tag(service: EntityService) -> None:
    document = service.create(label="田中太郎")
    assert document[RDFS_LABEL.value][0]["@language"] == "ja"


def test_an_explicit_language_is_honoured(service: EntityService) -> None:
    document = service.create(label="Taro Tanaka", language="en")
    assert document[RDFS_LABEL.value][0]["@language"] == "en"


def test_facts_land_in_the_data_graph(service: EntityService, runtime: Runtime) -> None:
    service.create(label="田中太郎", types=[PERSON])
    assert runtime.store.count(graphs.DATA) == 2
    assert runtime.store.count(graphs.ONTOLOGY) == 0


def test_literal_types_are_inferred_from_the_value(service: EntityService) -> None:
    document = service.create(label="田中太郎", properties={BIRTH_DATE: "1990-04-01"})
    assert document[BIRTH_DATE] == [
        {"@value": "1990-04-01", "@type": "http://www.w3.org/2001/XMLSchema#date"}
    ]


def test_a_declared_literal_type_wins(service: EntityService) -> None:
    document = service.create(
        label="x",
        properties={
            BIRTH_DATE: {"@value": "1990", "@type": "http://www.w3.org/2001/XMLSchema#string"}
        },
    )
    assert document[BIRTH_DATE][0]["@type"] == "http://www.w3.org/2001/XMLSchema#string"


def test_prefixed_names_are_expanded(service: EntityService) -> None:
    document = service.create(label="田中太郎", types=["ont:Person"])
    assert document["@type"] == [PERSON]


def test_relations_reference_another_node(service: EntityService) -> None:
    acme = service.create(label="株式会社アクメ", types=[ORGANIZATION])
    alice = service.create(
        label="田中太郎", types=[PERSON], properties={WORKS_FOR: {"@id": acme["@id"]}}
    )
    assert alice[WORKS_FOR][0]["@id"] == acme["@id"]


def test_get_returns_the_concise_bounded_description(service: EntityService) -> None:
    created = service.create(label="田中太郎", types=[PERSON])
    fetched = service.get(created["@id"])
    assert fetched["@id"] == created["@id"]
    assert fetched["@type"] == [PERSON]


def test_get_of_an_unknown_iri_raises(service: EntityService) -> None:
    with pytest.raises(EntityNotFoundError):
        service.get("https://example.org/kg/id/nobody")


def test_referenced_nodes_carry_their_label_so_clients_keep_context(
    service: EntityService,
) -> None:
    acme = service.create(label="株式会社アクメ", types=[ORGANIZATION])
    alice = service.create(label="田中太郎", properties={WORKS_FOR: {"@id": acme["@id"]}})
    reference = service.get(alice["@id"])[WORKS_FOR][0]
    assert reference[RDFS_LABEL.value] == [{"@value": "株式会社アクメ", "@language": "ja"}]


def test_get_with_a_depth_pulls_in_the_neighbourhood(service: EntityService) -> None:
    acme = service.create(label="株式会社アクメ", types=[ORGANIZATION])
    alice = service.create(label="田中太郎", properties={WORKS_FOR: {"@id": acme["@id"]}})
    document = service.get(alice["@id"], depth=2)
    assert {node["@id"] for node in document["@graph"]} == {alice["@id"], acme["@id"]}


def test_patch_adds_and_removes_triples(service: EntityService) -> None:
    created = service.create(label="田中太郎", properties={BIRTH_DATE: "1990-04-01"})
    patched = service.patch(
        created["@id"],
        add={WORKS_FOR: {"@id": "https://example.org/kg/id/acme"}},
        remove={BIRTH_DATE: "1990-04-01"},
    )
    assert BIRTH_DATE not in patched
    assert patched[WORKS_FOR][0]["@id"] == "https://example.org/kg/id/acme"


def test_renaming_changes_the_label_and_never_the_iri(service: EntityService) -> None:
    created = service.create(label="田中太郎")
    renamed = service.patch(created["@id"], label="田中 太郎")
    assert renamed["@id"] == created["@id"]
    assert renamed[RDFS_LABEL.value] == [{"@value": "田中 太郎", "@language": "ja"}]


def test_delete_removes_the_node_and_every_triple_pointing_at_it(
    service: EntityService, runtime: Runtime
) -> None:
    acme = service.create(label="株式会社アクメ")
    service.create(label="田中太郎", properties={WORKS_FOR: {"@id": acme["@id"]}})
    removed = service.delete(acme["@id"])
    assert removed == 2
    assert runtime.store.count(graphs.DATA) == 1
    with pytest.raises(EntityNotFoundError):
        service.get(acme["@id"])


def test_delete_of_an_unknown_iri_raises(service: EntityService) -> None:
    with pytest.raises(EntityNotFoundError):
        service.delete("https://example.org/kg/id/nobody")


def test_search_finds_a_node_by_its_label(service: EntityService) -> None:
    created = service.create(label="田中太郎", types=[PERSON])
    assert [hit["@id"] for hit in service.search(query="田中")] == [created["@id"]]


def test_search_can_be_narrowed_by_type(service: EntityService) -> None:
    person = service.create(label="田中太郎", types=[PERSON])
    service.create(label="田中商店", types=[ORGANIZATION])
    assert [hit["@id"] for hit in service.search(query="田中", type_iri=PERSON)] == [person["@id"]]


def test_search_reflects_a_rename(service: EntityService) -> None:
    created = service.create(label="田中太郎")
    service.patch(created["@id"], label="佐藤花子")
    assert service.search(query="田中") == []
    assert [hit["@id"] for hit in service.search(query="佐藤")] == [created["@id"]]


def test_search_forgets_a_deleted_node(service: EntityService) -> None:
    created = service.create(label="田中太郎")
    service.delete(created["@id"])
    assert service.search(query="田中") == []


def test_every_write_is_recorded_in_the_changelog(service: EntityService, runtime: Runtime) -> None:
    created = service.create(label="田中太郎")
    service.patch(created["@id"], label="佐藤花子")
    assert [patch.actor for patch in runtime.changelog.read_all()] == ["user", "user"]


def test_a_write_can_be_undone_and_redone(service: EntityService, runtime: Runtime) -> None:
    created = service.create(label="田中太郎")
    runtime.undo()
    with pytest.raises(EntityNotFoundError):
        service.get(created["@id"])
    runtime.redo()
    assert service.get(created["@id"])["@id"] == created["@id"]


def test_undo_also_rewinds_the_search_index(service: EntityService, runtime: Runtime) -> None:
    service.create(label="田中太郎")
    runtime.undo()
    assert service.search(query="田中") == []


def test_creating_without_a_label_is_rejected(service: EntityService) -> None:
    with pytest.raises(ValueError, match="label"):
        service.create(label="   ")


def test_rdf_type_cannot_be_smuggled_in_as_a_plain_property(service: EntityService) -> None:
    document = service.create(label="田中太郎", properties={RDF_TYPE.value: {"@id": PERSON}})
    assert document["@type"] == [PERSON]


def test_search_can_be_limited_to_instances(service: EntityService, runtime: Runtime) -> None:
    from ontoforge.ontology import OntologyService

    created = service.create(label="田中太郎", types=[PERSON])
    OntologyService(runtime).add_class(label="田中コーポレーション")

    assert len(service.search(query="田中")) == 2
    assert [hit["@id"] for hit in service.search(query="田中", kind="instance")] == [created["@id"]]


def test_search_can_be_limited_to_ontology_terms(service: EntityService, runtime: Runtime) -> None:
    from ontoforge.ontology import OntologyService

    service.create(label="田中太郎", types=[PERSON])
    term = OntologyService(runtime).add_class(label="田中コーポレーション")

    assert [hit["@id"] for hit in service.search(query="田中", kind="term")] == [term["@id"]]
