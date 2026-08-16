from __future__ import annotations

import re

from app.config import settings
from app.models.schemas import (
    ClassCreate,
    ClassUpdate,
    ConsistencyReportSchema,
    InconsistencySchema,
    OntologyClass,
    OwlClassCreateV2,
    OwlClassUpdateV2,
    OwlClassV2,
    OwlPropertyCreateV2,
    OwlPropertyUpdateV2,
    OwlPropertyV2,
    PropertyCreate,
    PropertyDef,
    Relationship,
    RelationshipCreate,
    RelationshipUpdate,
    SchemaResponse,
    SchemaV2Response,
    TripleSchema,
)
from app.ontology.consistency.service import ConsistencyService
from app.ontology.inference.service import InferenceService
from app.ontology.models.enums import (
    IRI_TO_CHARACTERISTIC,
    PropertyCharacteristic,
    PropertyType,
)
from app.ontology.models.owl_class import OwlClass
from app.ontology.models.owl_property import OwlProperty
from app.ontology.models.resource import Annotation
from app.ontology.rdf.mapper import RdfMapper
from app.ontology.tbox.dto_mapper import (
    create_v2_class,
    create_v2_property,
    owl_class_to_v2,
    owl_property_to_v2,
    update_v2_class,
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


class TBoxService:
    """OWL 2 DL TBox management backed by Oxigraph."""

    def __init__(self, store: OxigraphStore) -> None:
        self.store = store
        self.graph = store.ontology_graph
        self.mapper = RdfMapper()
        self.inference = InferenceService(store)
        self.consistency = ConsistencyService(store, self.inference)

    def list_classes(self) -> list[OntologyClass]:
        sparql = f"""
        PREFIX owl: <{R.OWL}>
        PREFIX rdfs: <{R.RDFS}>
        PREFIX kg: <{R.KG}>
        SELECT ?c ?label ?desc ?alias ?example ?parent WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            ?c a owl:Class ;
               rdfs:label ?label .
            FILTER(STRSTARTS(STR(?c), "{R.KG}class:"))
            OPTIONAL {{ ?c rdfs:comment ?desc }}
            OPTIONAL {{ ?c kg:alias ?alias }}
            OPTIONAL {{ ?c kg:example ?example }}
            OPTIONAL {{ ?c rdfs:subClassOf ?parent .
                        FILTER(STRSTARTS(STR(?parent), "{R.KG}class:")) }}
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
        applicable_domains = self._class_and_ancestors(class_id)
        return [
            prop
            for prop in self.list_properties()
            if not prop.domain or any(d in applicable_domains for d in prop.domain)
        ]

    def _class_and_ancestors(self, class_id: str) -> set[str]:
        ancestors: set[str] = {class_id}
        for cls in self.list_classes():
            if cls.id == class_id:
                ancestors.update(cls.parent_classes)
                for parent in list(cls.parent_classes):
                    ancestors.update(self._class_and_ancestors(parent))
                break
        return ancestors

    def create_class(self, data: ClassCreate) -> OntologyClass:
        uri = R.class_uri(data.id)
        owl_class = OwlClass(
            iri=uri,
            types=[R.OWL_CLASS],
            subclass_of=[R.class_uri(p) for p in data.parent_classes],
            annotations=self._build_class_annotations(data),
        )
        for triple in self.mapper.owl_class_to_triples(owl_class):
            self.store.add_triple(triple, self.graph)
        return self.get_class(data.id) or OntologyClass(id=data.id, label=data.label)

    def update_class(self, class_id: str, data: ClassUpdate) -> OntologyClass | None:
        existing = self.get_class(class_id)
        if not existing:
            return None
        self.store.remove_entity_quads(R.class_uri(class_id), self.graph)
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
        if not self.get_class(class_id):
            return False
        self.store.remove_entity_quads(R.class_uri(class_id), self.graph)
        return True

    def list_properties(self) -> list[PropertyDef]:
        sparql = f"""
        PREFIX owl: <{R.OWL}>
        PREFIX rdfs: <{R.RDFS}>
        PREFIX kg: <{R.KG}>
        SELECT ?p ?label ?desc ?domain ?range ?editorRequired ?alias WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            ?p a owl:DatatypeProperty ;
               rdfs:label ?label .
            FILTER(STRSTARTS(STR(?p), "{R.KG}property:"))
            OPTIONAL {{ ?p rdfs:comment ?desc }}
            OPTIONAL {{ ?p rdfs:domain ?domain .
                        FILTER(STRSTARTS(STR(?domain), "{R.KG}class:")) }}
            OPTIONAL {{ ?p rdfs:range ?range }}
            OPTIONAL {{ ?p kg:editorRequired ?editorRequired }}
            OPTIONAL {{ ?p kg:alias ?alias }}
          }}
        }}
        """
        rows = self.store.query(sparql)
        return self._aggregate_properties(rows, "property:")

    def list_object_properties(self) -> list[PropertyDef]:
        sparql = f"""
        PREFIX owl: <{R.OWL}>
        PREFIX rdfs: <{R.RDFS}>
        PREFIX kg: <{R.KG}>
        SELECT ?p ?label ?desc ?domain ?range ?editorRequired ?alias WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            ?p a owl:ObjectProperty ;
               rdfs:label ?label .
            FILTER(STRSTARTS(STR(?p), "{R.KG}relationship:"))
            OPTIONAL {{ ?p rdfs:comment ?desc }}
            OPTIONAL {{ ?p rdfs:domain ?domain .
                        FILTER(STRSTARTS(STR(?domain), "{R.KG}class:")) }}
            OPTIONAL {{ ?p rdfs:range ?range .
                        FILTER(STRSTARTS(STR(?range), "{R.KG}class:")) }}
            OPTIONAL {{ ?p kg:editorRequired ?editorRequired }}
            OPTIONAL {{ ?p kg:alias ?alias }}
          }}
        }}
        """
        rows = self.store.query(sparql)
        return self._aggregate_properties(rows, "relationship:")

    def _aggregate_properties(self, rows: list[dict[str, str]], prefix: str) -> list[PropertyDef]:
        props: dict[str, PropertyDef] = {}
        for row in rows:
            pid = R.local_name(row["p"]).replace(prefix, "")
            if pid not in props:
                props[pid] = PropertyDef(
                    id=pid,
                    label=row.get("label", pid),
                    description=row.get("desc", ""),
                    required=row.get("editorRequired", "").lower() == "true",
                )
            if row.get("domain"):
                did = R.class_id_from_uri(row["domain"])
                if did not in props[pid].domain:
                    props[pid].domain.append(did)
            if row.get("range"):
                rid = row["range"]
                if rid.startswith(R.KG):
                    rid = R.class_id_from_uri(rid)
                elif "#" in rid or ":" in rid:
                    rid = rid.rsplit("#", 1)[-1] if "#" in rid else rid.rsplit(":", 1)[-1]
                if rid not in props[pid].range:
                    props[pid].range.append(rid)
            if row.get("alias") and row["alias"] not in props[pid].aliases:
                props[pid].aliases.append(row["alias"])
        return list(props.values())

    def create_property(self, data: PropertyCreate) -> PropertyDef:
        uri = R.property_uri(data.id)
        prop = OwlProperty(
            iri=uri,
            types=[R.OWL_DATATYPE_PROPERTY],
            property_type=PropertyType.DATATYPE,
            domain=[R.class_uri(d) for d in data.domain],
            range_iris=[self._resolve_range(r) for r in data.range],
            editor_required=data.required,
            annotations=self._build_property_annotations(data),
        )
        for triple in self.mapper.owl_property_to_triples(prop):
            self.store.add_triple(triple, self.graph)
        for p in self.list_properties():
            if p.id == data.id:
                return p
        return PropertyDef(id=data.id, label=data.label, required=data.required)

    def get_object_property(self, prop_id: str) -> OwlProperty | None:
        uri = R.relationship_uri(prop_id)
        return self._load_property(uri, PropertyType.OBJECT)

    def create_object_property(self, data: RelationshipCreate) -> Relationship:
        uri = R.relationship_uri(data.id)
        prop = OwlProperty(
            iri=uri,
            types=[R.OWL_OBJECT_PROPERTY],
            property_type=PropertyType.OBJECT,
            domain=[R.class_uri(d) for d in data.domain],
            range_iris=[R.class_uri(r) for r in data.range],
            inverse_of=R.relationship_uri(data.inverse) if data.inverse else None,
            annotations=self._build_relationship_annotations(data),
        )
        for triple in self.mapper.owl_property_to_triples(prop):
            self.store.add_triple(triple, self.graph)
        return self.get_relationship(data.id) or Relationship(id=data.id, label=data.label)

    def get_relationship(self, rel_id: str) -> Relationship | None:
        for rel in self.list_relationships():
            if rel.id == rel_id:
                return rel
        return None

    def list_relationships(self) -> list[Relationship]:
        sparql = f"""
        PREFIX owl: <{R.OWL}>
        PREFIX rdfs: <{R.RDFS}>
        PREFIX kg: <{R.KG}>
        SELECT ?r ?label ?desc ?domain ?range ?inverse ?alias WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            ?r a owl:ObjectProperty ;
               rdfs:label ?label .
            FILTER(STRSTARTS(STR(?r), "{R.KG}relationship:"))
            OPTIONAL {{ ?r rdfs:comment ?desc }}
            OPTIONAL {{ ?r rdfs:domain ?domain .
                        FILTER(STRSTARTS(STR(?domain), "{R.KG}class:")) }}
            OPTIONAL {{ ?r rdfs:range ?range .
                        FILTER(STRSTARTS(STR(?range), "{R.KG}class:")) }}
            OPTIONAL {{ ?r owl:inverseOf ?inverse }}
            OPTIONAL {{ ?r kg:alias ?alias }}
          }}
        }}
        """
        rows = self.store.query(sparql)
        rels: dict[str, Relationship] = {}
        for row in rows:
            rid = R.local_name(row["r"]).replace("relationship:", "")
            if rid not in rels:
                inverse = row.get("inverse")
                rels[rid] = Relationship(
                    id=rid,
                    label=row.get("label", rid),
                    description=row.get("desc", ""),
                    inverse=R.local_name(inverse).replace("relationship:", "") if inverse else None,
                )
            if row.get("domain"):
                did = R.class_id_from_uri(row["domain"])
                if did not in rels[rid].domain:
                    rels[rid].domain.append(did)
            if row.get("range"):
                rng = R.class_id_from_uri(row["range"])
                if rng not in rels[rid].range:
                    rels[rid].range.append(rng)
            if row.get("alias") and row["alias"] not in rels[rid].aliases:
                rels[rid].aliases.append(row["alias"])
        return list(rels.values())

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
        return self.create_object_property(updated)

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

    def _load_property(self, uri: str, expected_type: PropertyType) -> OwlProperty | None:
        sparql = f"""
        PREFIX owl: <{R.OWL}>
        PREFIX rdfs: <{R.RDFS}>
        SELECT ?type ?domain ?range ?inverse WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            <{uri}> a ?type .
            OPTIONAL {{ <{uri}> rdfs:domain ?domain }}
            OPTIONAL {{ <{uri}> rdfs:range ?range }}
            OPTIONAL {{ <{uri}> owl:inverseOf ?inverse }}
          }}
        }}
        """
        rows = self.store.query(sparql)
        if not rows:
            return None
        characteristics: set[PropertyCharacteristic] = set()
        prop_type = expected_type
        domain: list[str] = []
        range_iris: list[str] = []
        inverse_of: str | None = None
        for row in rows:
            type_iri = row.get("type", "")
            char = IRI_TO_CHARACTERISTIC.get(type_iri)
            if char:
                characteristics.add(char)
            pt = self.mapper.property_type_from_iri(type_iri)
            if pt:
                prop_type = pt
            if row.get("domain"):
                domain.append(row["domain"])
            if row.get("range"):
                range_iris.append(row["range"])
            if row.get("inverse"):
                inverse_of = row["inverse"]
        type_iri = (
            R.OWL_OBJECT_PROPERTY if prop_type == PropertyType.OBJECT else R.OWL_DATATYPE_PROPERTY
        )
        return OwlProperty(
            iri=uri,
            types=[type_iri],
            property_type=prop_type,
            domain=domain,
            range_iris=range_iris,
            inverse_of=inverse_of,
            characteristics=characteristics,
        )

    @staticmethod
    def _resolve_range(range_value: str) -> str:
        if range_value.startswith("xsd:"):
            return f"{R.XSD}{range_value[4:]}"
        if range_value.startswith(R.XSD):
            return range_value
        return R.class_uri(range_value)

    @staticmethod
    def _build_class_annotations(data: ClassCreate) -> list[Annotation]:
        anns: list[Annotation] = []
        if data.label:
            anns.append(Annotation(property=R.RDFS_LABEL, value=data.label))
        if data.description:
            anns.append(Annotation(property=R.RDFS_COMMENT, value=data.description))
        for alias in data.aliases:
            anns.append(Annotation(property=R.KG_ALIAS, value=alias))
        for example in data.examples:
            anns.append(Annotation(property=R.KG_EXAMPLE, value=example))
        return anns

    @staticmethod
    def _build_property_annotations(data: PropertyCreate) -> list[Annotation]:
        anns: list[Annotation] = []
        if data.label:
            anns.append(Annotation(property=R.RDFS_LABEL, value=data.label))
        if data.description:
            anns.append(Annotation(property=R.RDFS_COMMENT, value=data.description))
        for alias in data.aliases:
            anns.append(Annotation(property=R.KG_ALIAS, value=alias))
        return anns

    @staticmethod
    def _build_relationship_annotations(data: RelationshipCreate) -> list[Annotation]:
        anns: list[Annotation] = []
        if data.label:
            anns.append(Annotation(property=R.RDFS_LABEL, value=data.label or data.id))
        if data.description:
            anns.append(Annotation(property=R.RDFS_COMMENT, value=data.description))
        for alias in data.aliases:
            anns.append(Annotation(property=R.KG_ALIAS, value=alias))
        return anns

    # --- v2 API ---

    def list_classes_v2(self) -> list[OwlClassV2]:
        result: list[OwlClassV2] = []
        for dto in self.list_classes():
            owl = self._load_owl_class(R.class_uri(dto.id))
            if owl:
                v2 = owl_class_to_v2(owl, dto.labels)
                v2.label = dto.label
                v2.description = dto.description
                v2.aliases = dto.aliases
                v2.examples = dto.examples
                result.append(v2)
        return result

    def get_class_v2(self, class_id: str) -> OwlClassV2 | None:
        dto = self.get_class(class_id)
        if not dto:
            return None
        owl = self._load_owl_class(R.class_uri(class_id))
        if not owl:
            return None
        v2 = owl_class_to_v2(owl, dto.labels)
        v2.label = dto.label
        v2.description = dto.description
        v2.aliases = dto.aliases
        v2.examples = dto.examples
        return v2

    def create_class_v2(self, data: OwlClassCreateV2) -> OwlClassV2:
        owl = create_v2_class(data)
        for triple in self.mapper.owl_class_to_triples(owl):
            self.store.add_triple(triple, self.graph)
        self.inference.apply_inferred()
        return self.get_class_v2(data.id) or OwlClassV2(iri=R.class_uri(data.id), id=data.id)

    def update_class_v2(self, class_id: str, data: OwlClassUpdateV2) -> OwlClassV2 | None:
        existing = self._load_owl_class(R.class_uri(class_id))
        if not existing:
            return None
        self.store.remove_entity_quads(R.class_uri(class_id), self.graph)
        updated = update_v2_class(existing, data)
        for triple in self.mapper.owl_class_to_triples(updated):
            self.store.add_triple(triple, self.graph)
        self.inference.apply_inferred()
        return self.get_class_v2(class_id)

    def list_properties_v2(self) -> list[OwlPropertyV2]:
        result: list[OwlPropertyV2] = []
        for dto in self.list_properties():
            owl = self._load_property(R.property_uri(dto.id), PropertyType.DATATYPE)
            if owl:
                v2 = owl_property_to_v2(owl)
                v2.label = dto.label
                v2.description = dto.description
                v2.aliases = dto.aliases
                v2.editor_required = dto.required
                result.append(v2)
        for dto in self.list_relationships():
            owl = self._load_property(R.relationship_uri(dto.id), PropertyType.OBJECT)
            if owl:
                v2 = owl_property_to_v2(owl)
                v2.label = dto.label
                v2.description = dto.description
                v2.aliases = dto.aliases
                v2.inverse_of = dto.inverse
                result.append(v2)
        return result

    def get_property_v2(self, prop_id: str) -> OwlPropertyV2 | None:
        for prop in self.list_properties_v2():
            if prop.id == prop_id:
                return prop
        return None

    def create_property_v2(self, data: OwlPropertyCreateV2) -> OwlPropertyV2:
        prop = create_v2_property(data)
        for triple in self.mapper.owl_property_to_triples(prop):
            self.store.add_triple(triple, self.graph)
        self.inference.apply_inferred()
        return self.get_property_v2(data.id) or OwlPropertyV2(
            iri=prop.iri,
            id=data.id,
            property_type=data.property_type,
        )

    def update_property_v2(self, prop_id: str, data: OwlPropertyUpdateV2) -> OwlPropertyV2 | None:
        existing = self.get_property_v2(prop_id)
        if not existing:
            return None
        uri = (
            R.relationship_uri(prop_id)
            if existing.property_type == PropertyType.OBJECT.value
            else R.property_uri(prop_id)
        )
        self.store.remove_entity_quads(uri, self.graph)
        create_data = OwlPropertyCreateV2(
            id=prop_id,
            label=data.label if data.label is not None else existing.label,
            description=data.description if data.description is not None else existing.description,
            property_type=existing.property_type,
            domain=data.domain if data.domain is not None else existing.domain,
            range=data.range if data.range is not None else existing.range,
            sub_property_of=data.sub_property_of
            if data.sub_property_of is not None
            else existing.sub_property_of,
            inverse_of=data.inverse_of if data.inverse_of is not None else existing.inverse_of,
            characteristics=data.characteristics
            if data.characteristics is not None
            else existing.characteristics,
            editor_required=data.editor_required
            if data.editor_required is not None
            else existing.editor_required,
            aliases=data.aliases if data.aliases is not None else existing.aliases,
        )
        return self.create_property_v2(create_data)

    def delete_property_v2(self, prop_id: str) -> bool:
        prop = self.get_property_v2(prop_id)
        if not prop:
            return False
        uri = (
            R.relationship_uri(prop_id)
            if prop.property_type == PropertyType.OBJECT.value
            else R.property_uri(prop_id)
        )
        self.store.remove_entity_quads(uri, self.graph)
        return True

    def get_schema_v2(self) -> SchemaV2Response:
        return SchemaV2Response(
            classes=self.list_classes_v2(),
            properties=self.list_properties_v2(),
        )

    def get_consistency_report(self) -> ConsistencyReportSchema:
        report = self.consistency.check()
        return ConsistencyReportSchema(
            consistent=report.consistent,
            inconsistencies=[
                InconsistencySchema(
                    code=i.code,
                    message=i.message,
                    involved_iris=i.involved_iris,
                )
                for i in report.inconsistencies
            ],
        )

    def list_inferred_triples(self) -> list[TripleSchema]:
        self.inference.apply_inferred()
        return [
            TripleSchema(
                subject=t.subject,
                predicate=t.predicate,
                object=t.object,
                object_is_literal=t.object_is_literal,
                literal_datatype=t.literal_datatype,
                literal_language=t.literal_language,
                source=t.source.value,
                category=t.category.value,
            )
            for t in self.inference.list_inferred_triples()
        ]

    def _load_owl_class(self, uri: str) -> OwlClass | None:
        sparql = f"""
        PREFIX owl: <{R.OWL}>
        PREFIX rdfs: <{R.RDFS}>
        SELECT ?p ?o ?label ?lang WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            <{uri}> ?p ?o .
            OPTIONAL {{
              <{uri}> rdfs:label ?label .
              BIND(LANG(?label) AS ?lang)
            }}
          }}
        }}
        """
        rows = self.store.query(sparql)
        if not rows:
            return None
        subclass_of: list[str] = []
        equivalent_class = []
        disjoint_with: list[str] = []
        annotations: list[Annotation] = []
        for row in rows:
            pred = row.get("p", "")
            obj = row.get("o", "")
            if pred == R.RDFS_SUBCLASS_OF and obj.startswith(R.KG + "class:"):
                subclass_of.append(obj)
            elif pred == R.OWL_EQUIVALENT_CLASS:
                pass  # complex expressions loaded separately in future
            elif pred == R.OWL_DISJOINT_WITH and obj.startswith(R.KG + "class:"):
                disjoint_with.append(obj)
            elif pred == R.RDFS_LABEL:
                annotations.append(
                    Annotation(property=pred, value=obj, language=row.get("lang") or None)
                )
            elif pred in (R.RDFS_COMMENT, R.KG_ALIAS, R.KG_EXAMPLE):
                annotations.append(Annotation(property=pred, value=obj))
        return OwlClass(
            iri=uri,
            types=[R.OWL_CLASS],
            subclass_of=subclass_of,
            equivalent_class=equivalent_class,
            disjoint_with=disjoint_with,
            annotations=annotations,
        )
