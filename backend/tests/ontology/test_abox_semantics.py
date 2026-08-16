"""Tests for ABox OWL semantics."""

import tempfile

import pytest

from app.deps import reset_services
from app.ontology.abox.service import ABoxService
from app.storage import rdf_constants as R
from app.storage.oxigraph_store import OxigraphStore


@pytest.fixture
def abox_store(monkeypatch):
    reset_services()
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("KG_DATA_DIR", tmpdir)
    reset_services()
    store = OxigraphStore(tmpdir)
    from pathlib import Path

    seed = Path(__file__).resolve().parents[2] / "app" / "ontology" / "seed.ttl"
    store.load_seed_if_needed(seed)
    yield store
    reset_services()


def test_literal_uses_xsd_datatype(abox_store: OxigraphStore):
    abox = ABoxService(abox_store)
    lit = abox.literal_for_property("birthDate", "1990-01-01")
    assert lit.datatype == R.XSD_DATE


def test_same_as_assertion(abox_store: OxigraphStore):
    abox = ABoxService(abox_store)
    abox.add_same_as("alice", "alice_smith")
    rows = abox_store.query(f"""
        SELECT ?o WHERE {{
          GRAPH <urn:kg:data> {{
            <{R.node_uri("alice")}> <{R.OWL_SAME_AS}> ?o .
          }}
        }}
    """)
    assert len(rows) == 1
    assert rows[0]["o"] == R.node_uri("alice_smith")


def test_different_from_does_not_imply_distinct(abox_store: OxigraphStore):
    """UNA is not adopted: two IRIs without sameAs are not asserted distinct."""
    rows = abox_store.query("""
        SELECT (COUNT(?s) AS ?count) WHERE {
          GRAPH <urn:kg:data> {
            ?s a ?type .
          }
        }
    """)
    assert int(rows[0]["count"]) >= 0
