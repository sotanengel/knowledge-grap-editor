import os
from pathlib import Path

from app.config import settings
from app.services.export_service import ExportService
from app.services.graph_service import GraphService
from app.services.ontology_service import OntologyService
from app.services.suggest_service import SuggestService
from app.services.validation_service import ValidationService
from app.storage.oxigraph_store import OxigraphStore

_store: OxigraphStore | None = None
_graph: GraphService | None = None
_ontology: OntologyService | None = None
_validation: ValidationService | None = None
_suggest: SuggestService | None = None
_export: ExportService | None = None


def get_store() -> OxigraphStore:
    global _store
    if _store is None:
        data_dir = os.environ.get("KG_DATA_DIR", settings.data_dir)
        _store = OxigraphStore(data_dir)
        seed = Path(__file__).resolve().parent.parent / "ontology" / "seed.ttl"
        _store.load_seed_if_needed(seed)
    return _store


def get_graph_service() -> GraphService:
    global _graph
    if _graph is None:
        _graph = GraphService(get_store())
    return _graph


def get_ontology_service() -> OntologyService:
    global _ontology
    if _ontology is None:
        _ontology = OntologyService(get_store())
    return _ontology


def get_validation_service() -> ValidationService:
    global _validation
    if _validation is None:
        _validation = ValidationService(get_ontology_service(), get_graph_service())
    return _validation


def get_suggest_service() -> SuggestService:
    global _suggest
    if _suggest is None:
        _suggest = SuggestService(get_ontology_service())
    return _suggest


def get_export_service() -> ExportService:
    global _export
    if _export is None:
        _export = ExportService(get_store())
    return _export


def reset_services() -> None:
    """Reset singletons for testing."""
    global _store, _graph, _ontology, _validation, _suggest, _export
    _store = _graph = _ontology = _validation = _suggest = _export = None
