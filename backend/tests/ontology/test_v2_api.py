"""Tests for v2 ontology API."""

from fastapi.testclient import TestClient


def test_v2_schema(api_client: TestClient):
    r = api_client.get("/api/ontology/v2/schema")
    assert r.status_code == 200
    data = r.json()
    assert "classes" in data
    assert "properties" in data
    class_ids = {c["id"] for c in data["classes"]}
    assert "Entity" in class_ids
    assert "Person" in class_ids


def test_v2_list_properties_unified(api_client: TestClient):
    r = api_client.get("/api/ontology/v2/properties")
    assert r.status_code == 200
    props = r.json()
    ids = {p["id"] for p in props}
    assert "name" in ids
    assert "worksFor" in ids
    name = next(p for p in props if p["id"] == "name")
    assert name["property_type"] == "DatatypeProperty"
    assert "FunctionalProperty" in name["characteristics"]
    works_for = next(p for p in props if p["id"] == "worksFor")
    assert works_for["property_type"] == "ObjectProperty"


def test_v2_create_object_property_with_characteristics(api_client: TestClient):
    r = api_client.post(
        "/api/ontology/v2/properties",
        json={
            "id": "marriedTo",
            "label": "married to",
            "property_type": "ObjectProperty",
            "domain": ["Person"],
            "range": ["Person"],
            "characteristics": ["SymmetricProperty"],
        },
    )
    assert r.status_code == 201
    assert "SymmetricProperty" in r.json()["characteristics"]


def test_v2_consistency(api_client: TestClient):
    r = api_client.get("/api/ontology/v2/consistency")
    assert r.status_code == 200
    assert r.json()["consistent"] is True


def test_v1_backward_compat(api_client: TestClient):
    r = api_client.get("/api/ontology/classes")
    assert r.status_code == 200
    assert any(c["id"] == "Person" for c in r.json())
