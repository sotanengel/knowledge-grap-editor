"""ABox OWL semantics service."""

from __future__ import annotations

from app.ontology.models.literal import LiteralValue
from app.ontology.rdf.mapper import RdfMapper
from app.storage import rdf_constants as R
from app.storage.oxigraph_store import OxigraphStore


class ABoxService:
    def __init__(self, store: OxigraphStore) -> None:
        self.store = store
        self.graph = store.data_graph
        self.mapper = RdfMapper()

    def literal_for_property(self, prop_id: str, value: str) -> LiteralValue:
        from app.config import settings

        rows = self.store.query(f"""
            SELECT ?range WHERE {{
              GRAPH <{settings.ontology_graph}> {{
                <{R.property_uri(prop_id)}> <{R.RDFS_RANGE}> ?range .
              }}
            }}
        """)
        datatype = R.XSD_STRING
        if rows:
            range_iri = rows[0]["range"]
            if range_iri.startswith(R.XSD):
                datatype = range_iri
        return LiteralValue(lexical=value, datatype=datatype)

    def add_datatype_assertion(self, subject: str, prop_id: str, value: str) -> None:
        lit = self.literal_for_property(prop_id, value)
        self.store.add_quad(
            R.node_uri(subject),
            R.property_uri(prop_id),
            self.store.literal(lit.lexical, lit.datatype),
            self.graph,
        )

    def add_same_as(self, subject: str, other: str) -> None:
        self.store.add_quad(
            R.node_uri(subject),
            R.OWL_SAME_AS,
            R.node_uri(other),
            self.graph,
        )

    def add_different_from(self, subject: str, other: str) -> None:
        self.store.add_quad(
            R.node_uri(subject),
            R.OWL_DIFFERENT_FROM,
            R.node_uri(other),
            self.graph,
        )

    def apply_node_properties(self, node_id: str, properties: dict[str, str]) -> None:
        for key, value in properties.items():
            self.add_datatype_assertion(node_id, key, value)
