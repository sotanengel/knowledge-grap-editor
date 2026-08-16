"""Tests for OWL inference."""

import tempfile

import pytest

from app.deps import reset_services
from app.ontology.inference.service import InferenceService
from app.storage import rdf_constants as R
from app.storage.oxigraph_store import OxigraphStore


@pytest.fixture
def inference_store(monkeypatch):
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


def test_subclass_type_inference(inference_store: OxigraphStore):
    store = inference_store
    store.add_quad(R.node_uri("alice"), R.RDF_TYPE, R.class_uri("Person"), store.data_graph)
    store.add_quad(
        R.node_uri("alice"),
        R.RDFS_LABEL,
        store.literal("Alice"),
        store.data_graph,
    )
    inference = InferenceService(store)
    inferred = inference.infer_all()
    type_triples = [t for t in inferred if t.predicate == R.RDF_TYPE]
    inferred_types = {t.object for t in type_triples}
    assert R.class_uri("Agent") in inferred_types or R.class_uri("Entity") in inferred_types


def test_symmetric_inference(inference_store: OxigraphStore):
    store = inference_store
    prop = R.relationship_uri("marriedTo")
    store.add_quad(prop, R.RDF_TYPE, R.OWL_OBJECT_PROPERTY, store.ontology_graph)
    store.add_quad(prop, R.RDF_TYPE, f"{R.OWL}SymmetricProperty", store.ontology_graph)
    store.add_quad(R.node_uri("a"), R.RDF_TYPE, R.class_uri("Person"), store.data_graph)
    store.add_quad(R.node_uri("b"), R.RDF_TYPE, R.class_uri("Person"), store.data_graph)
    store.add_quad(R.node_uri("a"), prop, R.node_uri("b"), store.data_graph)
    inference = InferenceService(store)
    inferred = inference.infer_all()
    assert any(
        t.subject == R.node_uri("b") and t.object == R.node_uri("a") and t.predicate == prop
        for t in inferred
    )
