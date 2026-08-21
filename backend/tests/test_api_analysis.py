from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pyoxigraph import Literal, NamedNode, Quad

from ontoforge.api.app import create_app
from ontoforge.namespaces import OWL_CLASS, RDF_TYPE, RDFS_LABEL, RDFS_SUBCLASS_OF
from ontoforge.runtime import Runtime
from ontoforge.store import graphs

ONT = "https://example.org/kg/ont#"
ID = "https://example.org/kg/id/"
PERSON = NamedNode(f"{ONT}Person")
EMPLOYEE = NamedNode(f"{ONT}Employee")
ALICE = NamedNode(f"{ID}alice")


@pytest.fixture
def client(runtime: Runtime) -> Iterator[TestClient]:
    runtime.write(
        additions=[
            Quad(PERSON, RDF_TYPE, OWL_CLASS, graphs.ONTOLOGY),
            Quad(PERSON, RDFS_LABEL, Literal("人物", language="ja"), graphs.ONTOLOGY),
            Quad(EMPLOYEE, RDF_TYPE, OWL_CLASS, graphs.ONTOLOGY),
            Quad(EMPLOYEE, RDFS_SUBCLASS_OF, PERSON, graphs.ONTOLOGY),
            Quad(ALICE, RDF_TYPE, EMPLOYEE, graphs.DATA),
            Quad(ALICE, RDFS_LABEL, Literal("田中太郎", language="ja"), graphs.DATA),
        ]
    )
    with TestClient(create_app(runtime=runtime)) as opened:
        yield opened


# ---------------------------------------------------------------- reasoning


def test_reasoning_reports_what_it_derived(client: TestClient) -> None:
    payload = client.post("/api/v1/reason", json={}).json()
    assert payload["derived"] >= 1
    assert payload["profile"] == "rdfs"


def test_reasoning_says_what_it_held_back_and_why(client: TestClient) -> None:
    # The closure is far larger than what belongs on a canvas, so "why is that
    # not shown?" needs an answer (§10.1).
    payload = client.post("/api/v1/reason", json={"profile": "owl2-rl"}).json()
    assert payload["suppressed"] > 0
    reasons = {entry["reason"] for entry in payload["suppressedByReason"]}
    assert reasons
    assert all(entry["explanation"] for entry in payload["suppressedByReason"])


def test_owl2_rl_is_offered_as_a_profile(client: TestClient) -> None:
    names = {entry["name"] for entry in client.get("/api/v1/reason/profiles").json()["profiles"]}
    assert names == {"none", "rdfs", "rl-lite", "owl2-rl"}


def test_the_profile_can_be_chosen_per_run(client: TestClient) -> None:
    assert client.post("/api/v1/reason", json={"profile": "none"}).json()["derived"] == 0


def test_an_unknown_profile_is_a_422(client: TestClient) -> None:
    assert client.post("/api/v1/reason", json={"profile": "owl-dl"}).status_code == 422


def test_the_profiles_are_listed_with_their_rules(client: TestClient) -> None:
    payload = client.get("/api/v1/reason/profiles").json()
    assert payload["current"] == "rdfs"
    by_name = {entry["name"]: entry for entry in payload["profiles"]}
    assert by_name["none"]["rules"] == []
    assert len(by_name["rl-lite"]["rules"]) > len(by_name["rdfs"]["rules"])
    assert all(rule["description"] for rule in by_name["rl-lite"]["rules"])


def test_a_derived_triple_can_be_explained(client: TestClient) -> None:
    client.post("/api/v1/reason", json={})
    payload = client.post(
        "/api/v1/reason/explain",
        json={"subject": ALICE.value, "predicate": RDF_TYPE.value, "object": PERSON.value},
    ).json()
    assert payload["premises"], payload
    # The premises must be the ones that actually carry the conclusion.
    text = " ".join(premise["text"] for premise in payload["premises"])
    assert "Employee" in text
    assert payload["rule"]


def test_explaining_an_asserted_triple_is_a_404(client: TestClient) -> None:
    client.post("/api/v1/reason", json={})
    response = client.post(
        "/api/v1/reason/explain",
        json={"subject": ALICE.value, "predicate": RDF_TYPE.value, "object": EMPLOYEE.value},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------- validation


def _shape() -> dict:
    return {
        "name": "person",
        "target_class": PERSON.value,
        "properties": [{"path": f"{ONT}birthDate", "min_count": 1}],
    }


def test_a_shape_can_be_saved_listed_and_deleted(client: TestClient) -> None:
    assert client.put("/api/v1/shapes/person", json=_shape()).status_code == 200
    assert client.get("/api/v1/shapes").json()["shapes"][0]["targetClass"] == PERSON.value
    assert client.delete("/api/v1/shapes/person").json()["removed"] > 0
    assert client.get("/api/v1/shapes").json()["shapes"] == []


def test_a_mismatched_shape_name_is_a_400(client: TestClient) -> None:
    assert client.put("/api/v1/shapes/other", json=_shape()).status_code == 400


def test_validation_conforms_when_nothing_is_constrained(client: TestClient) -> None:
    assert client.post("/api/v1/validate").json()["conforms"] is True


def test_validation_reports_violations_with_a_repair(client: TestClient) -> None:
    client.put("/api/v1/shapes/person", json=_shape())
    client.post("/api/v1/reason", json={})
    payload = client.post("/api/v1/validate").json()
    assert payload["conforms"] is False
    assert ALICE.value in payload["violated"]
    assert "田中太郎" in payload["findings"][0]["suggestion"]


def test_validation_survives_the_reasoners_provenance_records(client: TestClient) -> None:
    # The inferred graph holds RDF 1.2 triple terms; rdflib cannot read those,
    # so they must be filtered out of the SHACL bridge rather than crashing it.
    client.post("/api/v1/reason", json={})
    client.put("/api/v1/shapes/person", json=_shape())
    assert client.post("/api/v1/validate").status_code == 200


# ---------------------------------------------------------------- vocabularies


def test_the_bundled_vocabularies_are_offered(client: TestClient) -> None:
    payload = client.get("/api/v1/vocabularies").json()
    names = {entry["name"] for entry in payload["available"]}
    assert {"schema", "skos", "foaf", "dcterms", "prov"} <= names
    assert payload["loaded"] == []


def test_a_vocabulary_can_be_loaded_without_touching_the_network(client: TestClient) -> None:
    loaded = client.post("/api/v1/vocabularies", json={"names": ["skos"]}).json()["loaded"]
    assert loaded["skos"] > 100
    assert client.get("/api/v1/vocabularies").json()["loaded"] == ["skos"]


def test_an_unknown_vocabulary_is_a_404(client: TestClient) -> None:
    assert client.post("/api/v1/vocabularies", json={"names": ["wingdings"]}).status_code == 404


def test_a_loaded_vocabulary_stays_out_of_the_authored_graphs(
    client: TestClient, runtime: Runtime
) -> None:
    before = runtime.store.count(graphs.DATA)
    client.post("/api/v1/vocabularies", json={"names": ["skos"]})
    assert runtime.store.count(graphs.DATA) == before
