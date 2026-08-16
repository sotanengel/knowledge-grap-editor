"""Tests for v1 to v2 ontology migration."""

import tempfile
from pathlib import Path

import pytest

from app.deps import reset_services
from app.ontology.migration.v1_to_v2 import migrate_ontology_v1_to_v2, needs_v2_migration
from app.storage import rdf_constants as R
from app.storage.oxigraph_store import OxigraphStore


@pytest.fixture
def v1_store(monkeypatch):
    reset_services()
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("KG_DATA_DIR", tmpdir)
    reset_services()
    store = OxigraphStore(tmpdir)
    seed = Path(__file__).resolve().parents[2] / "app" / "ontology" / "seed_v1.ttl"
    if not seed.exists():
        seed = Path(__file__).resolve().parents[2] / "app" / "ontology" / "seed.ttl"
    store.load_seed_if_needed(seed)
    yield store
    reset_services()


def test_needs_v2_migration_detects_rdfs_class(v1_store: OxigraphStore):
    assert needs_v2_migration(v1_store)


def test_migrate_converts_rdfs_class_to_owl_class(v1_store: OxigraphStore):
    migrate_ontology_v1_to_v2(v1_store)
    results = v1_store.query(f"""
        PREFIX owl: <{R.OWL}>
        SELECT ?c WHERE {{
          GRAPH <urn:kg:ontology> {{
            <{R.class_uri("Person")}> a owl:Class .
            FILTER NOT EXISTS {{ <{R.class_uri("Person")}> a <{R.RDFS}Class> }}
          }}
        }}
    """)
    assert len(results) >= 1


def test_migrate_converts_property_to_datatype_property(v1_store: OxigraphStore):
    migrate_ontology_v1_to_v2(v1_store)
    results = v1_store.query(f"""
        PREFIX owl: <{R.OWL}>
        SELECT ?p WHERE {{
          GRAPH <urn:kg:ontology> {{
            <{R.property_uri("name")}> a owl:DatatypeProperty .
          }}
        }}
    """)
    assert len(results) >= 1


def test_migrate_required_to_editor_required(v1_store: OxigraphStore):
    migrate_ontology_v1_to_v2(v1_store)
    results = v1_store.query(f"""
        SELECT ?v WHERE {{
          GRAPH <urn:kg:ontology> {{
            <{R.property_uri("birthDate")}> <{R.KG_EDITOR_REQUIRED}> ?v .
          }}
        }}
    """)
    assert results
    assert results[0]["v"].lower() == "true"
    old = v1_store.query(f"""
        SELECT ?v WHERE {{
          GRAPH <urn:kg:ontology> {{
            <{R.property_uri("birthDate")}> <{R.KG_REQUIRED}> ?v .
          }}
        }}
    """)
    assert len(old) == 0


def test_migrate_adds_entity_root(v1_store: OxigraphStore):
    migrate_ontology_v1_to_v2(v1_store)
    results = v1_store.query(f"""
        PREFIX owl: <{R.OWL}>
        SELECT ?p WHERE {{
          GRAPH <urn:kg:ontology> {{
            <{R.class_uri("Entity")}> a owl:Class .
            <{R.class_uri("Agent")}> <{R.RDFS_SUBCLASS_OF}> <{R.class_uri("Entity")}> .
          }}
        }}
    """)
    assert len(results) >= 1


def test_migrate_name_gets_functional_property(v1_store: OxigraphStore):
    migrate_ontology_v1_to_v2(v1_store)
    results = v1_store.query(f"""
        PREFIX owl: <{R.OWL}>
        SELECT ?p WHERE {{
          GRAPH <urn:kg:ontology> {{
            <{R.property_uri("name")}> a owl:FunctionalProperty .
          }}
        }}
    """)
    assert len(results) >= 1


def test_migrate_preserves_class_iri(v1_store: OxigraphStore):
    migrate_ontology_v1_to_v2(v1_store)
    results = v1_store.query(f"""
        SELECT ?label WHERE {{
          GRAPH <urn:kg:ontology> {{
            <{R.class_uri("Organization")}> <{R.RDFS_LABEL}> ?label .
          }}
        }}
    """)
    labels = {r["label"] for r in results}
    assert "Organization" in labels or "組織" in labels
