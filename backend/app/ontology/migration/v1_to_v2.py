from __future__ import annotations

import os
from datetime import UTC, datetime

from app.config import settings
from app.storage import rdf_constants as R
from app.storage.oxigraph_store import OxigraphStore

MIGRATION_MARKER = ".ontology_v2_migrated"
RDF_PROPERTY = f"{R.RDF}Property"
RDFS_CLASS = f"{R.RDFS}Class"
FUNCTIONAL_PROPERTY = f"{R.OWL}FunctionalProperty"


def _migration_marker_path(store: OxigraphStore) -> str:
    return os.path.join(store.data_dir, MIGRATION_MARKER)


def is_migrated(store: OxigraphStore) -> bool:
    return os.path.exists(_migration_marker_path(store))


def needs_v2_migration(store: OxigraphStore) -> bool:
    if is_migrated(store):
        return False
    sparql = f"""
        PREFIX rdfs: <{R.RDFS}>
        SELECT (COUNT(?c) AS ?count) WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            ?c a rdfs:Class .
          }}
        }}
    """
    result = store.query(sparql)
    return int(result[0]["count"]) > 0 if result else False


def migrate_ontology_v1_to_v2(store: OxigraphStore) -> None:
    """Transform v1 ontology triples in-place to OWL 2 DL compliant form."""
    if is_migrated(store):
        return

    # Declare annotation properties
    store.add_quad(R.KG_ALIAS, R.RDF_TYPE, R.OWL_ANNOTATION_PROPERTY, store.ontology_graph)
    store.add_quad(R.KG_EXAMPLE, R.RDF_TYPE, R.OWL_ANNOTATION_PROPERTY, store.ontology_graph)
    store.add_quad(
        R.KG_EDITOR_REQUIRED, R.RDF_TYPE, R.OWL_ANNOTATION_PROPERTY, store.ontology_graph
    )

    # rdfs:Class -> owl:Class
    classes = store.query(f"""
        PREFIX rdfs: <{R.RDFS}>
        SELECT ?c WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            ?c a rdfs:Class .
          }}
        }}
    """)
    for row in classes:
        uri = row["c"]
        store.add_quad(uri, R.RDF_TYPE, R.OWL_CLASS, store.ontology_graph)
        _remove_type_quad(store, uri, RDFS_CLASS)

    # rdf:Property -> owl:DatatypeProperty
    props = store.query(f"""
        PREFIX rdf: <{R.RDF}>
        SELECT ?p WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            ?p a rdf:Property .
          }}
        }}
    """)
    for row in props:
        uri = row["p"]
        store.add_quad(uri, R.RDF_TYPE, R.OWL_DATATYPE_PROPERTY, store.ontology_graph)
        _remove_type_quad(store, uri, RDF_PROPERTY)

    # kg:required -> kg:editorRequired
    required_rows = store.query(f"""
        SELECT ?p ?v WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            ?p <{R.KG_REQUIRED}> ?v .
          }}
        }}
    """)
    for row in required_rows:
        prop_uri = row["p"]
        value = row["v"]
        store.add_quad(
            prop_uri,
            R.KG_EDITOR_REQUIRED,
            store.literal(value.lower() == "true", R.XSD_BOOLEAN),
            store.ontology_graph,
        )
        _remove_quad(store, prop_uri, R.KG_REQUIRED, value)

    # name property gets FunctionalProperty
    store.add_quad(
        R.property_uri("name"),
        R.RDF_TYPE,
        FUNCTIONAL_PROPERTY,
        store.ontology_graph,
    )
    store.add_quad(
        R.property_uri("name"),
        R.RDFS_DOMAIN,
        R.class_uri("Entity"),
        store.ontology_graph,
    )

    # Add Entity root class if missing
    entity_uri = R.class_uri("Entity")
    existing_entity = store.query(f"""
        SELECT (COUNT(?p) AS ?count) WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            <{entity_uri}> ?p ?o .
          }}
        }}
    """)
    if not existing_entity or int(existing_entity[0]["count"]) == 0:
        store.add_quad(entity_uri, R.RDF_TYPE, R.OWL_CLASS, store.ontology_graph)
        store.add_quad(
            entity_uri,
            R.RDFS_LABEL,
            store.literal("Entity"),
            store.ontology_graph,
        )
        store.add_quad(
            entity_uri,
            R.RDFS_LABEL,
            store.literal("エンティティ", language="ja"),
            store.ontology_graph,
        )

    # Agent subClassOf Entity
    agent_uri = R.class_uri("Agent")
    store.add_quad(agent_uri, R.RDFS_SUBCLASS_OF, entity_uri, store.ontology_graph)

    # Non-Agent top-level classes subClassOf Entity
    for class_id in ("Product", "Place", "Event", "Document", "Project", "Software"):
        store.add_quad(
            R.class_uri(class_id),
            R.RDFS_SUBCLASS_OF,
            entity_uri,
            store.ontology_graph,
        )

    with open(_migration_marker_path(store), "w", encoding="utf-8") as f:
        f.write(datetime.now(UTC).isoformat())


def _remove_type_quad(store: OxigraphStore, subject: str, type_iri: str) -> None:
    from pyoxigraph import NamedNode, Quad

    s = NamedNode(subject)
    p = NamedNode(R.RDF_TYPE)
    o = NamedNode(type_iri)
    quad = Quad(s, p, o, store.ontology_graph)
    if quad in store.store:
        store.store.remove(quad)


def _remove_quad(store: OxigraphStore, subject: str, predicate: str, obj_value: str) -> None:
    from pyoxigraph import NamedNode

    s = NamedNode(subject)
    p = NamedNode(predicate)
    for quad in store.store.quads_for_pattern(s, p, None, store.ontology_graph):
        o_str = str(quad.object.value) if hasattr(quad.object, "value") else str(quad.object)
        if o_str.lower() == obj_value.lower():
            store.store.remove(quad)


def run_migration_if_needed(store: OxigraphStore) -> None:
    if needs_v2_migration(store):
        migrate_ontology_v1_to_v2(store)
