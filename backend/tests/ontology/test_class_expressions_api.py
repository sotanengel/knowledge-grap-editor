"""Tests for ClassExpression TBox CRUD via v2 API."""

from fastapi.testclient import TestClient


def test_create_class_with_disjoint(api_client: TestClient):
    r = api_client.post(
        "/api/ontology/v2/classes",
        json={
            "id": "Cat",
            "label": "Cat",
            "subclass_of": ["Entity"],
            "disjoint_with": ["Dog"],
            "force": True,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert "Cat" in data["id"]
    assert any(d == "Dog" or d == "urn:kg:class:Dog" for d in data["disjoint_with"])


def test_create_class_with_restriction_equivalent(api_client: TestClient):
    r = api_client.post(
        "/api/ontology/v2/classes",
        json={
            "id": "Parent",
            "label": "Parent",
            "equivalent_class": [
                {
                    "kind": "intersection",
                    "operands": [
                        {"kind": "named", "iri": "urn:kg:class:Person"},
                        {
                            "kind": "restriction",
                            "on_property": "urn:kg:relationship:hasChild",
                            "restriction_kind": "someValuesFrom",
                            "filler": {"kind": "named", "iri": "urn:kg:class:Person"},
                        },
                    ],
                }
            ],
            "force": True,
        },
    )
    assert r.status_code == 201
    assert r.json()["id"] == "Parent"
    stored = api_client.get("/api/ontology/v2/classes/Parent")
    assert stored.status_code == 200
