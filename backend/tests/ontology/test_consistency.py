"""Tests for OWL consistency checking."""

import tempfile

import pytest

from app.deps import reset_services
from app.ontology.consistency.service import ConsistencyService
from app.ontology.inference.service import InferenceService
from app.storage import rdf_constants as R
from app.storage.oxigraph_store import OxigraphStore


@pytest.fixture
def consistency_store(monkeypatch):
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


def test_consistent_ontology(consistency_store: OxigraphStore):
    svc = ConsistencyService(consistency_store, InferenceService(consistency_store))
    report = svc.check()
    assert report.consistent


def test_disjoint_class_inconsistency(consistency_store: OxigraphStore):
    store = consistency_store
    store.add_quad(
        R.class_uri("Cat"),
        R.OWL_DISJOINT_WITH,
        R.class_uri("Dog"),
        store.ontology_graph,
    )
    store.add_quad(R.node_uri("alice"), R.RDF_TYPE, R.class_uri("Cat"), store.data_graph)
    store.add_quad(R.node_uri("alice"), R.RDF_TYPE, R.class_uri("Dog"), store.data_graph)
    svc = ConsistencyService(store, InferenceService(store))
    report = svc.check()
    assert not report.consistent
    assert any(i.code == "DISJOINT_CLASS_VIOLATION" for i in report.inconsistencies)


def test_functional_property_inconsistency(consistency_store: OxigraphStore):
    store = consistency_store
    name_uri = R.property_uri("name")
    store.add_quad(R.node_uri("alice"), name_uri, store.literal("Alice"), store.data_graph)
    store.add_quad(R.node_uri("alice"), name_uri, store.literal("Bob"), store.data_graph)
    svc = ConsistencyService(store, InferenceService(store))
    report = svc.check()
    assert not report.consistent
    assert any(i.code == "FUNCTIONAL_PROPERTY_VIOLATION" for i in report.inconsistencies)
