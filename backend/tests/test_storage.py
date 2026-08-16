import os
import tempfile

import pytest

from app.deps import reset_services
from app.storage.oxigraph_store import OxigraphStore


@pytest.fixture
def temp_store(monkeypatch):
    reset_services()
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("KG_DATA_DIR", tmpdir)
    reset_services()
    store = OxigraphStore(tmpdir)
    seed = os.path.join(os.path.dirname(__file__), "..", "ontology", "seed.ttl")
    store.load_seed_if_needed(__import__("pathlib").Path(seed))
    yield store
    reset_services()


def test_seed_ontology_loaded(temp_store: OxigraphStore):
    results = temp_store.query("""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(?c) AS ?count) WHERE {
          GRAPH <urn:kg:ontology> {
            ?c a rdfs:Class .
          }
        }
    """)
    assert int(results[0]["count"]) >= 5


def test_add_and_query_node(temp_store: OxigraphStore):
    from app.models.schemas import NodeCreate
    from app.services.graph_service import GraphService

    graph = GraphService(temp_store)
    node = graph.create_node(
        NodeCreate(
            id="org_001", label="Apple", type="Organization", properties={"name": "Apple Inc."}
        )
    )
    assert node.id == "org_001"
    assert node.label == "Apple"
    fetched = graph.get_node("org_001")
    assert fetched is not None
    assert fetched.type == "Organization"
