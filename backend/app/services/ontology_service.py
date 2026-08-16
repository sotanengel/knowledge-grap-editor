"""Backward-compatible ontology service delegating to TBoxService."""

from __future__ import annotations

from app.models.schemas import (
    ClassCreate,
    ClassUpdate,
    OntologyClass,
    PropertyCreate,
    PropertyDef,
    Relationship,
    RelationshipCreate,
    RelationshipUpdate,
    SchemaResponse,
)
from app.ontology.tbox.service import TBoxService
from app.storage.oxigraph_store import OxigraphStore


class OntologyService:
    """Thin wrapper around TBoxService for v1 API compatibility."""

    def __init__(self, store: OxigraphStore) -> None:
        self._tbox = TBoxService(store)
        self.store = store
        self.graph = store.ontology_graph

    def list_classes(self) -> list[OntologyClass]:
        return self._tbox.list_classes()

    def get_class(self, class_id: str) -> OntologyClass | None:
        return self._tbox.get_class(class_id)

    def get_class_properties(self, class_id: str) -> list[PropertyDef]:
        return self._tbox.get_class_properties(class_id)

    def create_class(self, data: ClassCreate) -> OntologyClass:
        return self._tbox.create_class(data)

    def update_class(self, class_id: str, data: ClassUpdate) -> OntologyClass | None:
        return self._tbox.update_class(class_id, data)

    def delete_class(self, class_id: str) -> bool:
        return self._tbox.delete_class(class_id)

    def list_properties(self) -> list[PropertyDef]:
        return self._tbox.list_properties()

    def create_property(self, data: PropertyCreate) -> PropertyDef:
        return self._tbox.create_property(data)

    def list_relationships(self) -> list[Relationship]:
        return self._tbox.list_relationships()

    def get_relationship(self, rel_id: str) -> Relationship | None:
        return self._tbox.get_relationship(rel_id)

    def create_relationship(self, data: RelationshipCreate) -> Relationship:
        return self._tbox.create_object_property(data)

    def update_relationship(self, rel_id: str, data: RelationshipUpdate) -> Relationship | None:
        return self._tbox.update_relationship(rel_id, data)

    def delete_relationship(self, rel_id: str) -> bool:
        return self._tbox.delete_relationship(rel_id)

    def get_schema(self) -> SchemaResponse:
        return self._tbox.get_schema()

    @property
    def tbox(self) -> TBoxService:
        return self._tbox
