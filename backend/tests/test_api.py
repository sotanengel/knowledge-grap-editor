from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pyoxigraph import Literal, NamedNode, Quad

from ontoforge.api.app import create_app
from ontoforge.api.routes.events import stream_events
from ontoforge.config import Settings
from ontoforge.runtime import Runtime
from ontoforge.store import graphs

PERSON = "https://example.org/kg/ont#Person"
WORKS_FOR = "https://example.org/kg/ont#worksFor"
LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

TURTLE = """
@prefix ex: <https://example.org/kg/id/> .
@prefix ont: <https://example.org/kg/ont#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
ex:alice a ont:Person ; rdfs:label "田中太郎"@ja .
"""


@pytest.fixture
def client(runtime: Runtime) -> Iterator[TestClient]:
    with TestClient(create_app(runtime=runtime)) as opened:
        yield opened


def _create(client: TestClient, label: str, **body: object) -> dict:
    response = client.post("/api/v1/entities", json={"label": label, **body})
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------- health & auth


def test_health_reports_the_store_size(client: TestClient) -> None:
    payload = client.get("/api/v1/health").json()
    assert payload["status"] == "ok"
    assert payload["quads"] == 0


def test_without_a_configured_token_no_authentication_is_required(client: TestClient) -> None:
    assert client.get("/api/v1/entities").status_code == 200


def test_a_configured_token_is_enforced(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data", auth_token="s3cret")
    with Runtime.create(settings) as runtime, TestClient(create_app(runtime=runtime)) as client:
        assert client.get("/api/v1/entities").status_code == 401
        assert (
            client.get("/api/v1/entities", headers={"Authorization": "Bearer nope"}).status_code
            == 403
        )
        ok = client.get("/api/v1/entities", headers={"Authorization": "Bearer s3cret"})
        assert ok.status_code == 200


# ---------------------------------------------------------------- entities


def test_creating_an_entity_returns_201_and_its_iri(client: TestClient) -> None:
    document = _create(client, "田中太郎", types=[PERSON])
    assert document["@id"].startswith("https://example.org/kg/id/")
    assert document["@type"] == [PERSON]


def test_creating_without_a_label_is_a_422(client: TestClient) -> None:
    assert client.post("/api/v1/entities", json={"label": "   "}).status_code == 422


def test_an_entity_can_be_fetched_by_its_percent_encoded_iri(client: TestClient) -> None:
    created = _create(client, "田中太郎")
    response = client.get(f"/api/v1/entities/{created['@id']}")
    assert response.status_code == 200
    assert response.json()["@id"] == created["@id"]


def test_fetching_an_unknown_entity_is_a_404(client: TestClient) -> None:
    assert client.get("/api/v1/entities/https://example.org/kg/id/nope").status_code == 404


def test_a_depth_query_returns_a_graph_document(client: TestClient) -> None:
    acme = _create(client, "株式会社アクメ")
    alice = _create(client, "田中太郎", properties={WORKS_FOR: {"@id": acme["@id"]}})
    payload = client.get(f"/api/v1/entities/{alice['@id']}", params={"depth": 2}).json()
    assert {node["@id"] for node in payload["@graph"]} == {alice["@id"], acme["@id"]}


def test_patching_adds_and_removes(client: TestClient) -> None:
    created = _create(client, "田中太郎", properties={WORKS_FOR: {"@id": "https://x/a"}})
    response = client.patch(
        f"/api/v1/entities/{created['@id']}",
        json={"remove": {WORKS_FOR: {"@id": "https://x/a"}}, "label": "佐藤花子"},
    )
    assert response.status_code == 200
    assert WORKS_FOR not in response.json()
    assert response.json()[LABEL][0]["@value"] == "佐藤花子"


def test_deleting_returns_the_number_of_triples_removed(client: TestClient) -> None:
    created = _create(client, "田中太郎")
    response = client.delete(f"/api/v1/entities/{created['@id']}")
    assert response.status_code == 200
    assert response.json()["removed"] == 1
    assert client.get(f"/api/v1/entities/{created['@id']}").status_code == 404


def test_listing_searches_by_label(client: TestClient) -> None:
    created = _create(client, "田中太郎", types=[PERSON])
    _create(client, "佐藤花子")
    payload = client.get("/api/v1/entities", params={"q": "田中"}).json()
    assert [node["@id"] for node in payload["@graph"]] == [created["@id"]]


def test_listing_can_be_narrowed_by_type_and_paged(client: TestClient) -> None:
    _create(client, "田中太郎", types=[PERSON])
    _create(client, "田中商店")
    payload = client.get("/api/v1/entities", params={"q": "田中", "type": PERSON}).json()
    assert len(payload["@graph"]) == 1
    assert client.get("/api/v1/entities", params={"limit": 1}).json()["limit"] == 1


# ---------------------------------------------------------------- ontology


def test_classes_and_properties_can_be_defined(client: TestClient) -> None:
    person = client.post("/api/v1/ontology/classes", json={"label": "人物"})
    assert person.status_code == 201
    assert person.json()["@id"] == "https://example.org/kg/ont#人物"
    prop = client.post("/api/v1/ontology/properties", json={"label": "所属", "domain": "ont:人物"})
    assert prop.status_code == 201


def test_the_ontology_tree_is_returned(client: TestClient) -> None:
    client.post("/api/v1/ontology/classes", json={"label": "人物"})
    client.post("/api/v1/ontology/classes", json={"label": "社員", "parents": ["ont:人物"]})
    tree = client.get("/api/v1/ontology").json()
    assert [child["label"] for child in tree["classes"][0]["children"]] == ["社員"]


def test_candidate_properties_are_offered_for_a_domain(client: TestClient) -> None:
    client.post("/api/v1/ontology/classes", json={"label": "人物"})
    client.post("/api/v1/ontology/properties", json={"label": "所属", "domain": "ont:人物"})
    candidates = client.get("/api/v1/ontology/properties", params={"domain": "ont:人物"}).json()
    assert [item["label"] for item in candidates["properties"]] == ["所属"]


def test_a_term_can_be_renamed(client: TestClient) -> None:
    client.post("/api/v1/ontology/classes", json={"label": "人物"})
    response = client.post("/api/v1/ontology/rename", json={"iri": "ont:人物", "label": "Person"})
    assert response.json()["@id"] == "https://example.org/kg/ont#Person"


def test_renaming_an_unknown_term_is_a_404(client: TestClient) -> None:
    response = client.post("/api/v1/ontology/rename", json={"iri": "ont:Nope", "label": "X"})
    assert response.status_code == 404


# ---------------------------------------------------------------- SPARQL


def test_a_select_query_returns_sparql_json(client: TestClient) -> None:
    _create(client, "田中太郎")
    response = client.get("/sparql", params={"query": "SELECT ?s WHERE { GRAPH ?g { ?s ?p ?o } }"})
    assert response.status_code == 200
    assert response.json()["results"]["bindings"]


def test_an_ask_query_returns_a_boolean(client: TestClient) -> None:
    assert client.get("/sparql", params={"query": "ASK { ?s ?p ?o }"}).json()["boolean"] is False


def test_a_construct_query_returns_turtle(client: TestClient) -> None:
    _create(client, "田中太郎")
    response = client.get(
        "/sparql",
        params={"query": "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"},
    )
    assert response.headers["content-type"].startswith("text/turtle")
    assert "田中太郎" in response.text


def test_a_query_can_be_posted(client: TestClient) -> None:
    response = client.post(
        "/sparql",
        content="SELECT ?s WHERE { ?s ?p ?o }",
        headers={"Content-Type": "application/sparql-query"},
    )
    assert response.status_code == 200


def test_an_update_sent_to_the_query_endpoint_is_refused(client: TestClient) -> None:
    response = client.get("/sparql", params={"query": "CLEAR ALL"})
    assert response.status_code == 400
    assert "read-only" in response.json()["detail"]


def test_a_syntactically_broken_query_is_a_400(client: TestClient) -> None:
    assert client.get("/sparql", params={"query": "SELECT ?s WHERE {"}).status_code == 400


def test_the_update_endpoint_writes_and_is_recorded(client: TestClient, runtime: Runtime) -> None:
    response = client.post(
        "/sparql/update",
        content=(
            "INSERT DATA { GRAPH <urn:ontoforge:data> { "
            '<https://example.org/kg/id/a> <http://www.w3.org/2000/01/rdf-schema#label> "あ"@ja } }'
        ),
        headers={"Content-Type": "application/sparql-update"},
    )
    assert response.status_code == 200
    assert runtime.store.count() == 1
    assert runtime.changelog.read_all()[-1].actor == "sparql-update"


def test_a_read_query_sent_to_the_update_endpoint_is_refused(client: TestClient) -> None:
    assert client.post("/sparql/update", content="SELECT ?s WHERE { ?s ?p ?o }").status_code == 400


# ---------------------------------------------------------------- import / export


def test_a_turtle_file_can_be_imported(client: TestClient) -> None:
    response = client.post(
        "/api/v1/import",
        files={"file": ("people.ttl", TURTLE.encode("utf-8"), "text/turtle")},
    )
    assert response.status_code == 200
    assert response.json()["quads"] == 2


def test_an_unsupported_upload_is_a_400(client: TestClient) -> None:
    response = client.post("/api/v1/import", files={"file": ("x.docx", b"nope", "text/plain")})
    assert response.status_code == 400


def test_a_csv_upload_needs_a_mapping(client: TestClient) -> None:
    response = client.post("/api/v1/import", files={"file": ("x.csv", b"a,b\n1,2\n", "text/csv")})
    assert response.status_code == 400


def test_a_csv_upload_with_a_mapping_creates_instances(client: TestClient) -> None:
    mapping = {
        "name": "people",
        "key_column": "key",
        "label_column": "name",
        "types": [PERSON],
        "columns": [],
    }
    response = client.post(
        "/api/v1/import",
        files={"file": ("people.csv", "key,name\n1,田中太郎\n".encode(), "text/csv")},
        data={"mapping": json.dumps(mapping)},
    )
    assert response.status_code == 200
    assert response.json()["rows"] == 1


@pytest.mark.parametrize(
    ("export_format", "content_type"),
    [
        ("turtle", "text/turtle"),
        ("trig", "application/trig"),
        ("jsonld", "application/ld+json"),
        ("graphml", "application/graphml+xml"),
        ("mermaid", "text/vnd.mermaid"),
        ("csv", "application/zip"),
    ],
)
def test_export_serves_each_format(
    client: TestClient, export_format: str, content_type: str
) -> None:
    _create(client, "田中太郎")
    response = client.get("/api/v1/export", params={"format": export_format})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_type)


def test_an_unknown_export_format_is_a_400(client: TestClient) -> None:
    assert client.get("/api/v1/export", params={"format": "wingdings"}).status_code == 400


def test_export_can_select_named_graphs(client: TestClient) -> None:
    _create(client, "田中太郎")
    response = client.get(
        "/api/v1/export", params={"format": "trig", "graphs": "urn:ontoforge:ontology"}
    )
    assert "田中太郎" not in response.text


def test_saved_mappings_can_be_listed_and_reused(client: TestClient) -> None:
    mapping = {"name": "people", "label_column": "name", "columns": []}
    assert client.put("/api/v1/mappings/people", json=mapping).status_code == 200
    assert client.get("/api/v1/mappings").json()["names"] == ["people"]
    assert client.get("/api/v1/mappings/people").json()["label_column"] == "name"


def test_loading_an_unknown_mapping_is_a_404(client: TestClient) -> None:
    assert client.get("/api/v1/mappings/nope").status_code == 404


# ---------------------------------------------------------------- history


def test_history_lists_changes_newest_first(client: TestClient) -> None:
    _create(client, "田中太郎")
    _create(client, "佐藤花子")
    entries = client.get("/api/v1/history").json()["entries"]
    assert [entry["seq"] for entry in entries] == [2, 1]
    assert entries[0]["actor"] == "user"


def test_undo_and_redo_move_through_the_history(client: TestClient) -> None:
    created = _create(client, "田中太郎")
    assert client.post("/api/v1/history/undo").json()["seq"] == 2
    assert client.get(f"/api/v1/entities/{created['@id']}").status_code == 404
    assert client.post("/api/v1/history/redo").json()["seq"] == 3
    assert client.get(f"/api/v1/entities/{created['@id']}").status_code == 200


def test_undo_with_nothing_to_undo_is_a_409(client: TestClient) -> None:
    assert client.post("/api/v1/history/undo").status_code == 409


# ---------------------------------------------------------------- events


@pytest.mark.anyio
async def test_the_event_stream_frames_the_ready_event_and_every_change(runtime: Runtime) -> None:
    # Driven against the endpoint's own generator: httpx's ASGI transport
    # buffers whole responses, so an endless stream cannot be read through it.
    response = await stream_events(runtime)
    frames = response.body_iterator

    ready = await anext(frames)
    assert ready.startswith("event: ready")
    assert json.loads(ready.split("data: ", 1)[1]) == {"seq": 0}

    runtime.write(
        additions=[
            Quad(
                NamedNode("https://example.org/kg/id/a"),
                NamedNode(LABEL),
                Literal("あ", language="ja"),
                graphs.DATA,
            )
        ]
    )
    change = await anext(frames)
    await frames.aclose()

    assert change.startswith("event: change")
    assert json.loads(change.split("data: ", 1)[1])["actor"] == "user"


@pytest.mark.anyio
async def test_a_closed_stream_stops_receiving_events(runtime: Runtime) -> None:
    response = await stream_events(runtime)
    frames = response.body_iterator
    await anext(frames)
    assert runtime.events.subscriber_count == 1
    await frames.aclose()
    assert runtime.events.subscriber_count == 0


def test_the_event_route_is_registered(client: TestClient) -> None:
    assert "/api/v1/events" in client.app.openapi()["paths"]


def test_listing_can_separate_instances_from_ontology_terms(client: TestClient) -> None:
    person = _create(client, "田中太郎")
    client.post("/api/v1/ontology/classes", json={"label": "田中商会"})

    instances = client.get("/api/v1/entities", params={"q": "田中", "kind": "instance"}).json()
    terms = client.get("/api/v1/entities", params={"q": "田中", "kind": "term"}).json()

    assert [node["@id"] for node in instances["@graph"]] == [person["@id"]]
    assert [node["@id"] for node in terms["@graph"]] == ["https://example.org/kg/ont#田中商会"]


def test_an_unknown_kind_is_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/entities", params={"kind": "nonsense"}).status_code == 422
