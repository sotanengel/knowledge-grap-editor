from __future__ import annotations

import re

from app.config import settings
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
from app.storage import rdf_constants as R
from app.storage.oxigraph_store import OxigraphStore

_JA_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]")


def _has_japanese(text: str) -> bool:
    return bool(_JA_RE.search(text))


def _pick_display_label(labels: list[str], aliases: list[str], class_id: str) -> str:
    for lbl in labels:
        if _has_japanese(lbl):
            return lbl
    for alias in aliases:
        if _has_japanese(alias):
            return alias
    return labels[0] if labels else class_id


class OntologyService:
    def __init__(self, store: OxigraphStore) -> None:
        self.store = store
        self.graph = store.ontology_graph

    def list_classes(self) -> list[OntologyClass]:
        sparql = f"""
        PREFIX rdfs: <{R.RDFS}>
        PREFIX kg: <{R.KG}>
        SELECT ?c ?label ?desc ?alias ?example ?parent WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            ?c a rdfs:Class ;
               rdfs:label ?label .
            FILTER(STRSTARTS(STR(?c), "{R.KG}class:"))
            OPTIONAL {{ ?c rdfs:comment ?desc }}
            OPTIONAL {{ ?c kg:alias ?alias }}
            OPTIONAL {{ ?c kg:example ?example }}
            OPTIONAL {{ ?c rdfs:subClassOf ?parent }}
          }}
        }}
        """
        rows = self.store.query(sparql)
        classes: dict[str, OntologyClass] = {}
        for row in rows:
            cid = R.class_id_from_uri(row["c"])
            if cid not in classes:
                classes[cid] = OntologyClass(
                    id=cid,
                    label=row.get("label", cid),
                    labels=[],
                    description=row.get("desc", ""),
                    aliases=[],
                    parent_classes=[],
                    examples=[],
                )
            if row.get("label"):
                lbl = row["label"]
                if lbl not in classes[cid].labels:
                    classes[cid].labels.append(lbl)
            if row.get("alias"):
                if row["alias"] not in classes[cid].aliases:
                    classes[cid].aliases.append(row["alias"])
            if row.get("example"):
                if row["example"] not in classes[cid].examples:
                    classes[cid].examples.append(row["example"])
            if row.get("parent"):
                parent_id = R.class_id_from_uri(row["parent"])
                if parent_id not in classes[cid].parent_classes:
                    classes[cid].parent_classes.append(parent_id)
        for cls in classes.values():
            cls.label = _pick_display_label(cls.labels, cls.aliases, cls.id)
        return list(classes.values())

    def get_class(self, class_id: str) -> OntologyClass | None:
        for cls in self.list_classes():
            if cls.id == class_id:
                return cls
        return None

    def get_class_properties(self, class_id: str) -> list[PropertyDef]:
        if not self.get_class(class_id):
            return []
        return [
            prop
            for prop in self.list_properties()
            if not prop.domain or class_id in prop.domain
        ]

    def create_class(self, data: ClassCreate) -> OntologyClass:
        uri = R.class_uri(data.id)
        self.store.add_quad(uri, R.RDF_TYPE, f"{R.RDFS}Class", self.graph)
        self.store.add_quad(uri, R.RDFS_LABEL, self.store.literal(data.label), self.graph)
        if data.description:
            self.store.add_quad(
                uri, R.RDFS_COMMENT, self.store.literal(data.description), self.graph
            )
        for alias in data.aliases:
            self.store.add_quad(uri, R.KG_ALIAS, self.store.literal(alias), self.graph)
        for example in data.examples:
            self.store.add_quad(uri, R.KG_EXAMPLE, self.store.literal(example), self.graph)
        for parent in data.parent_classes:
            self.store.add_quad(uri, R.RDFS_SUBCLASS_OF, R.class_uri(parent), self.graph)
        return self.get_class(data.id) or OntologyClass(id=data.id, label=data.label)

    def update_class(self, class_id: str, data: ClassUpdate) -> OntologyClass | None:
        existing = self.get_class(class_id)
        if not existing:
            return None
        uri = R.class_uri(class_id)
        self.store.remove_entity_quads(uri, self.graph)
        updated = ClassCreate(
            id=class_id,
            label=data.label or existing.label,
            description=data.description if data.description is not None else existing.description,
            aliases=data.aliases if data.aliases is not None else existing.aliases,
            parent_classes=data.parent_classes
            if data.parent_classes is not None
            else existing.parent_classes,
            examples=data.examples if data.examples is not None else existing.examples,
        )
        return self.create_class(updated)

    def delete_class(self, class_id: str) -> bool:
        existing = self.get_class(class_id)
        if not existing:
            return False
        self.store.remove_entity_quads(R.class_uri(class_id), self.graph)
        return True

    def list_properties(self) -> list[PropertyDef]:
        sparql = f"""
        PREFIX rdf: <{R.RDF}>
        PREFIX rdfs: <{R.RDFS}>
        PREFIX kg: <{R.KG}>
        SELECT ?p ?label ?desc ?domain ?range ?required ?alias WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            ?p a rdf:Property ;
               rdfs:label ?label .
            FILTER(STRSTARTS(STR(?p), "{R.KG}property:"))
            OPTIONAL {{ ?p rdfs:comment ?desc }}
            OPTIONAL {{ ?p rdfs:domain ?domain }}
            OPTIONAL {{ ?p rdfs:range ?range }}
            OPTIONAL {{ ?p kg:required ?required }}
            OPTIONAL {{ ?p kg:alias ?alias }}
          }}
        }}
        """
        rows = self.store.query(sparql)
        props: dict[str, PropertyDef] = {}
        for row in rows:
            pid = R.local_name(row["p"]).replace("property:", "")
            if pid not in props:
                props[pid] = PropertyDef(
                    id=pid,
                    label=row.get("label", pid),
                    description=row.get("desc", ""),
                    required=row.get("required", "").lower() == "true",
                )
            if row.get("domain"):
                did = R.class_id_from_uri(row["domain"])
                if did not in props[pid].domain:
                    props[pid].domain.append(did)
            if row.get("range"):
                rid = R.class_id_from_uri(row["range"])
                if rid not in props[pid].range:
                    props[pid].range.append(rid)
            if row.get("alias"):
                props[pid].aliases.append(row["alias"])
        return list(props.values())

    def create_property(self, data: PropertyCreate) -> PropertyDef:
        uri = R.property_uri(data.id)
        self.store.add_quad(uri, R.RDF_TYPE, f"{R.RDF}Property", self.graph)
        self.store.add_quad(
            uri, R.RDFS_LABEL, self.store.literal(data.label or data.id), self.graph
        )
        if data.description:
            self.store.add_quad(
                uri, R.RDFS_COMMENT, self.store.literal(data.description), self.graph
            )
        for d in data.domain:
            self.store.add_quad(uri, R.RDFS_DOMAIN, R.class_uri(d), self.graph)
        for r in data.range:
            self.store.add_quad(uri, R.RDFS_RANGE, R.class_uri(r), self.graph)
        if data.required:
            self.store.add_quad(
                uri,
                R.KG_REQUIRED,
                self.store.literal(True, f"{R.XSD}boolean"),
                self.graph,
            )
        for alias in data.aliases:
            self.store.add_quad(uri, R.KG_ALIAS, self.store.literal(alias), self.graph)
        for p in self.list_properties():
            if p.id == data.id:
                return p
        return PropertyDef(id=data.id, label=data.label)

    def list_relationships(self) -> list[Relationship]:
        sparql = f"""
        PREFIX owl: <{R.OWL}>
        PREFIX rdfs: <{R.RDFS}>
        PREFIX kg: <{R.KG}>
        SELECT ?r ?label ?desc ?domain ?range ?alias WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            ?r a owl:ObjectProperty ;
               rdfs:label ?label .
            FILTER(STRSTARTS(STR(?r), "{R.KG}relationship:"))
            OPTIONAL {{ ?r rdfs:comment ?desc }}
            OPTIONAL {{ ?r rdfs:domain ?domain }}
            OPTIONAL {{ ?r rdfs:range ?range }}
            OPTIONAL {{ ?r kg:alias ?alias }}
          }}
        }}
        """
        rows = self.store.query(sparql)
        rels: dict[str, Relationship] = {}
        for row in rows:
            rid = R.local_name(row["r"]).replace("relationship:", "")
            if rid not in rels:
                rels[rid] = Relationship(
                    id=rid,
                    label=row.get("label", rid),
                    description=row.get("desc", ""),
                )
            if row.get("domain"):
                did = R.class_id_from_uri(row["domain"])
                if did not in rels[rid].domain:
                    rels[rid].domain.append(did)
            if row.get("range"):
                rng = R.class_id_from_uri(row["range"])
                if rng not in rels[rid].range:
                    rels[rid].range.append(rng)
            if row.get("alias"):
                rels[rid].aliases.append(row["alias"])
        return list(rels.values())

    def get_relationship(self, rel_id: str) -> Relationship | None:
        for rel in self.list_relationships():
            if rel.id == rel_id:
                return rel
        return None

    def create_relationship(self, data: RelationshipCreate) -> Relationship:
        uri = R.relationship_uri(data.id)
        self.store.add_quad(uri, R.RDF_TYPE, R.OWL_OBJECT_PROPERTY, self.graph)
        self.store.add_quad(
            uri, R.RDFS_LABEL, self.store.literal(data.label or data.id), self.graph
        )
        if data.description:
            self.store.add_quad(
                uri, R.RDFS_COMMENT, self.store.literal(data.description), self.graph
            )
        for d in data.domain:
            self.store.add_quad(uri, R.RDFS_DOMAIN, R.class_uri(d), self.graph)
        for r in data.range:
            self.store.add_quad(uri, R.RDFS_RANGE, R.class_uri(r), self.graph)
        for alias in data.aliases:
            self.store.add_quad(uri, R.KG_ALIAS, self.store.literal(alias), self.graph)
        return self.get_relationship(data.id) or Relationship(id=data.id, label=data.label)

    def update_relationship(self, rel_id: str, data: RelationshipUpdate) -> Relationship | None:
        existing = self.get_relationship(rel_id)
        if not existing:
            return None
        self.store.remove_entity_quads(R.relationship_uri(rel_id), self.graph)
        updated = RelationshipCreate(
            id=rel_id,
            label=data.label or existing.label,
            description=data.description if data.description is not None else existing.description,
            domain=data.domain if data.domain is not None else existing.domain,
            range=data.range if data.range is not None else existing.range,
            inverse=data.inverse if data.inverse is not None else existing.inverse,
            aliases=data.aliases if data.aliases is not None else existing.aliases,
        )
        return self.create_relationship(updated)

    def delete_relationship(self, rel_id: str) -> bool:
        if not self.get_relationship(rel_id):
            return False
        self.store.remove_entity_quads(R.relationship_uri(rel_id), self.graph)
        return True

    def get_schema(self) -> SchemaResponse:
        return SchemaResponse(
            classes=self.list_classes(),
            properties=self.list_properties(),
            relationships=self.list_relationships(),
        )
