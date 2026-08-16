import tempfile

import pytest
from fastapi.testclient import TestClient

from app.deps import reset_services
from app.main import app


@pytest.fixture
def client(monkeypatch):
    reset_services()
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("KG_DATA_DIR", tmpdir)
    reset_services()
    with TestClient(app) as c:
        yield c
    reset_services()


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200


def test_list_ontology_classes(client: TestClient):
    r = client.get("/api/ontology/classes")
    assert r.status_code == 200
    classes = r.json()
    ids = {c["id"] for c in classes}
    assert "Organization" in ids
    assert "Person" in ids


def test_node_crud(client: TestClient):
    r = client.post(
        "/api/nodes",
        json={
            "id": "p1",
            "label": "山田太郎",
            "type": "Person",
            "properties": {"name": "山田太郎"},
        },
    )
    assert r.status_code == 201
    r = client.get("/api/nodes/p1")
    assert r.status_code == 200
    assert r.json()["label"] == "山田太郎"
    r = client.put("/api/nodes/p1", json={"label": "山田次郎"})
    assert r.status_code == 200
    assert r.json()["label"] == "山田次郎"
    r = client.delete("/api/nodes/p1")
    assert r.status_code == 204


def test_edge_with_validation_warning(client: TestClient):
    client.post("/api/nodes", json={"id": "prod1", "label": "iPhone", "type": "Product"})
    client.post("/api/nodes", json={"id": "org1", "label": "Apple", "type": "Organization"})
    # worksFor domain is Person, Product -> Organization should warn in error mode
    # In warn mode, edge should still be created
    r = client.post(
        "/api/edges",
        json={
            "id": "e1",
            "subject": "prod1",
            "predicate": "worksFor",
            "object": "org1",
        },
    )
    assert r.status_code == 201


def test_type_suggest(client: TestClient):
    r = client.get("/api/ontology/suggest?q=会社")
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) > 0
    assert results[0]["id"] == "Organization"


def test_graph_search(client: TestClient):
    client.post("/api/nodes", json={"id": "apple", "label": "Apple", "type": "Organization"})
    r = client.get("/api/graph/search?q=Apple")
    assert r.status_code == 200
    assert len(r.json()["nodes"]) >= 1


def test_export_turtle(client: TestClient):
    r = client.get("/api/export?format=turtle")
    assert r.status_code == 200
    assert "text/turtle" in r.headers["content-type"]
