from __future__ import annotations

from app.ontology.expressions.class_expression import (
    ClassExpression,
    ComplementExpression,
    IntersectionExpression,
    NamedClassExpression,
    OneOfExpression,
    RestrictionExpression,
    RestrictionKind,
    UnionExpression,
)
from app.ontology.models.enums import (
    CHARACTERISTIC_IRIS,
    IRI_TO_CHARACTERISTIC,
    PropertyCharacteristic,
    PropertyType,
)
from app.ontology.models.literal import LiteralValue
from app.ontology.models.owl_class import OwlClass
from app.ontology.models.owl_property import OwlProperty
from app.ontology.models.resource import Annotation
from app.ontology.models.triple import Triple, TripleCategory
from app.ontology.rdf import constants as C
from app.storage import rdf_constants as R


class RdfMapper:
    """Bidirectional mapping between OWL domain models and RDF triples."""

    _blank_counter = 0

    def _next_blank(self, prefix: str = "b") -> str:
        self._blank_counter += 1
        return f"_:{prefix}{self._blank_counter}"

    def _annotation_triples(
        self,
        subject: str,
        annotations: list[Annotation],
    ) -> list[Triple]:
        triples: list[Triple] = []
        for ann in annotations:
            triples.append(
                Triple(
                    subject=subject,
                    predicate=ann.property,
                    object=ann.value,
                    object_is_literal=True,
                    literal_language=ann.language,
                    literal_datatype=ann.datatype,
                    category=TripleCategory.ANNOTATION,
                )
            )
        return triples

    def class_expression_to_triples(
        self,
        expr: ClassExpression,
        blank_node: str | None = None,
    ) -> list[Triple]:
        node = blank_node or self._next_blank("ce")
        triples: list[Triple] = []

        if isinstance(expr, NamedClassExpression):
            triples.append(
                Triple(subject=node, predicate=C.RDF_TYPE, object=C.OWL_CLASS)
            )
            triples.append(Triple(subject=node, predicate=C.RDF_TYPE, object=expr.iri))
            return triples

        if isinstance(expr, IntersectionExpression):
            triples.append(
                Triple(subject=node, predicate=C.RDF_TYPE, object=C.OWL_CLASS)
            )
            list_node = self._next_blank("list")
            triples.append(
                Triple(subject=node, predicate=C.OWL_INTERSECTION_OF, object=list_node)
            )
            triples.extend(self._rdf_list_to_triples(list_node, expr.operands))
            return triples

        if isinstance(expr, UnionExpression):
            triples.append(
                Triple(subject=node, predicate=C.RDF_TYPE, object=C.OWL_CLASS)
            )
            list_node = self._next_blank("list")
            triples.append(Triple(subject=node, predicate=C.OWL_UNION_OF, object=list_node))
            triples.extend(self._rdf_list_to_triples(list_node, expr.operands))
            return triples

        if isinstance(expr, ComplementExpression):
            triples.append(
                Triple(subject=node, predicate=C.RDF_TYPE, object=C.OWL_CLASS)
            )
            if expr.operand:
                operand_node = self._next_blank("op")
                triples.append(
                    Triple(subject=node, predicate=C.OWL_COMPLEMENT_OF, object=operand_node)
                )
                triples.extend(self.class_expression_to_triples(expr.operand, operand_node))
            return triples

        if isinstance(expr, OneOfExpression):
            triples.append(
                Triple(subject=node, predicate=C.RDF_TYPE, object=C.OWL_CLASS)
            )
            list_node = self._next_blank("list")
            triples.append(Triple(subject=node, predicate=C.OWL_ONE_OF, object=list_node))
            triples.extend(self._iri_list_to_triples(list_node, expr.individuals))
            return triples

        if isinstance(expr, RestrictionExpression):
            triples.append(
                Triple(subject=node, predicate=C.RDF_TYPE, object=C.OWL_RESTRICTION)
            )
            triples.append(
                Triple(subject=node, predicate=C.OWL_ON_PROPERTY, object=expr.on_property)
            )
            pred = C.RESTRICTION_PREDICATE_MAP.get(expr.restriction_kind.value)
            if pred:
                if expr.restriction_kind == RestrictionKind.HAS_SELF:
                    triples.append(
                        Triple(
                            subject=node,
                            predicate=pred,
                            object="true",
                            object_is_literal=True,
                            literal_datatype=f"{C.XSD}boolean",
                        )
                    )
                elif expr.restriction_kind in (
                    RestrictionKind.CARDINALITY,
                    RestrictionKind.MIN,
                    RestrictionKind.MAX,
                ):
                    triples.append(
                        Triple(
                            subject=node,
                            predicate=pred,
                            object=str(expr.cardinality or 0),
                            object_is_literal=True,
                            literal_datatype=f"{C.XSD}nonNegativeInteger",
                        )
                    )
                elif isinstance(expr.filler, ClassExpression):
                    filler_node = self._next_blank("fill")
                    triples.append(Triple(subject=node, predicate=pred, object=filler_node))
                    triples.extend(self.class_expression_to_triples(expr.filler, filler_node))
                elif isinstance(expr.filler, str):
                    triples.append(Triple(subject=node, predicate=pred, object=expr.filler))
            return triples

        raise ValueError(f"Unsupported ClassExpression: {expr}")

    def _rdf_list_to_triples(
        self,
        list_head: str,
        operands: list[ClassExpression],
    ) -> list[Triple]:
        triples: list[Triple] = []
        current = list_head
        for i, operand in enumerate(operands):
            operand_node = self._next_blank("item")
            triples.append(
                Triple(subject=current, predicate=f"{C.RDF}first", object=operand_node)
            )
            triples.extend(self.class_expression_to_triples(operand, operand_node))
            if i < len(operands) - 1:
                rest_node = self._next_blank("rest")
                triples.append(
                    Triple(subject=current, predicate=f"{C.RDF}rest", object=rest_node)
                )
                current = rest_node
            else:
                triples.append(
                    Triple(
                        subject=current,
                        predicate=f"{C.RDF}rest",
                        object=f"{C.RDF}nil",
                    )
                )
        return triples

    def _iri_list_to_triples(self, list_head: str, iris: list[str]) -> list[Triple]:
        triples: list[Triple] = []
        current = list_head
        for i, iri in enumerate(iris):
            triples.append(Triple(subject=current, predicate=f"{C.RDF}first", object=iri))
            if i < len(iris) - 1:
                rest_node = self._next_blank("rest")
                triples.append(
                    Triple(subject=current, predicate=f"{C.RDF}rest", object=rest_node)
                )
                current = rest_node
            else:
                triples.append(
                    Triple(subject=current, predicate=f"{C.RDF}rest", object=f"{C.RDF}nil")
                )
        return triples

    def owl_class_to_triples(self, cls: OwlClass) -> list[Triple]:
        triples: list[Triple] = []
        for t in cls.types:
            triples.append(
                Triple(
                    subject=cls.iri,
                    predicate=C.RDF_TYPE,
                    object=t,
                    category=TripleCategory.TBOX,
                )
            )
        for parent in cls.subclass_of:
            if isinstance(parent, str):
                triples.append(
                    Triple(
                        subject=cls.iri,
                        predicate=C.RDFS_SUBCLASS_OF,
                        object=parent,
                        category=TripleCategory.TBOX,
                    )
                )
            else:
                parent_node = self._next_blank("sc")
                triples.append(
                    Triple(
                        subject=cls.iri,
                        predicate=C.RDFS_SUBCLASS_OF,
                        object=parent_node,
                        category=TripleCategory.TBOX,
                    )
                )
                triples.extend(self.class_expression_to_triples(parent, parent_node))
        for equiv in cls.equivalent_class:
            equiv_node = self._next_blank("eq")
            triples.append(
                Triple(
                    subject=cls.iri,
                    predicate=C.OWL_EQUIVALENT_CLASS,
                    object=equiv_node,
                    category=TripleCategory.TBOX,
                )
            )
            triples.extend(self.class_expression_to_triples(equiv, equiv_node))
        for disjoint in cls.disjoint_with:
            if isinstance(disjoint, str):
                triples.append(
                    Triple(
                        subject=cls.iri,
                        predicate=C.OWL_DISJOINT_WITH,
                        object=disjoint,
                        category=TripleCategory.TBOX,
                    )
                )
            else:
                disjoint_node = self._next_blank("dj")
                triples.append(
                    Triple(
                        subject=cls.iri,
                        predicate=C.OWL_DISJOINT_WITH,
                        object=disjoint_node,
                        category=TripleCategory.TBOX,
                    )
                )
                triples.extend(self.class_expression_to_triples(disjoint, disjoint_node))
        triples.extend(self._annotation_triples(cls.iri, cls.annotations))
        return triples

    def owl_property_to_triples(self, prop: OwlProperty) -> list[Triple]:
        triples: list[Triple] = []
        type_iri = {
            PropertyType.OBJECT: C.OWL_OBJECT_PROPERTY,
            PropertyType.DATATYPE: C.OWL_DATATYPE_PROPERTY,
            PropertyType.ANNOTATION: C.OWL_ANNOTATION_PROPERTY,
        }[prop.property_type]
        triples.append(
            Triple(
                subject=prop.iri,
                predicate=C.RDF_TYPE,
                object=type_iri,
                category=TripleCategory.TBOX,
            )
        )
        for characteristic in prop.characteristics:
            triples.append(
                Triple(
                    subject=prop.iri,
                    predicate=C.RDF_TYPE,
                    object=CHARACTERISTIC_IRIS[characteristic],
                    category=TripleCategory.TBOX,
                )
            )
        for d in prop.domain:
            if isinstance(d, str):
                triples.append(
                    Triple(
                        subject=prop.iri,
                        predicate=C.RDFS_DOMAIN,
                        object=d,
                        category=TripleCategory.TBOX,
                    )
                )
            else:
                d_node = self._next_blank("dom")
                triples.append(
                    Triple(
                        subject=prop.iri,
                        predicate=C.RDFS_DOMAIN,
                        object=d_node,
                        category=TripleCategory.TBOX,
                    )
                )
                triples.extend(self.class_expression_to_triples(d, d_node))
        for r in prop.range_iris:
            if isinstance(r, str):
                triples.append(
                    Triple(
                        subject=prop.iri,
                        predicate=C.RDFS_RANGE,
                        object=r,
                        category=TripleCategory.TBOX,
                    )
                )
            else:
                r_node = self._next_blank("rng")
                triples.append(
                    Triple(
                        subject=prop.iri,
                        predicate=C.RDFS_RANGE,
                        object=r_node,
                        category=TripleCategory.TBOX,
                    )
                )
                triples.extend(self.class_expression_to_triples(r, r_node))
        for sub in prop.sub_property_of:
            triples.append(
                Triple(
                    subject=prop.iri,
                    predicate=C.RDFS_SUB_PROPERTY_OF,
                    object=sub,
                    category=TripleCategory.TBOX,
                )
            )
        if prop.inverse_of:
            triples.append(
                Triple(
                    subject=prop.iri,
                    predicate=C.OWL_INVERSE_OF,
                    object=prop.inverse_of,
                    category=TripleCategory.TBOX,
                )
            )
        if prop.editor_required:
            triples.append(
                Triple(
                    subject=prop.iri,
                    predicate=C.KG_EDITOR_REQUIRED,
                    object="true",
                    object_is_literal=True,
                    literal_datatype=f"{C.XSD}boolean",
                    category=TripleCategory.ANNOTATION,
                )
            )
        triples.extend(self._annotation_triples(prop.iri, prop.annotations))
        return triples

    @staticmethod
    def is_annotation_predicate(predicate: str) -> bool:
        return predicate in C.ANNOTATION_PROPERTIES

    @staticmethod
    def characteristic_from_iri(iri: str) -> PropertyCharacteristic | None:
        return IRI_TO_CHARACTERISTIC.get(iri)

    @staticmethod
    def property_type_from_iri(iri: str) -> PropertyType | None:
        mapping = {
            C.OWL_OBJECT_PROPERTY: PropertyType.OBJECT,
            C.OWL_DATATYPE_PROPERTY: PropertyType.DATATYPE,
            C.OWL_ANNOTATION_PROPERTY: PropertyType.ANNOTATION,
        }
        return mapping.get(iri)

    @staticmethod
    def literal_to_value(literal: str, datatype: str | None, language: str | None) -> LiteralValue:
        return LiteralValue(lexical=literal, datatype=datatype, language=language)

    @staticmethod
    def local_id_from_iri(iri: str) -> str:
        return R.local_name(iri).split(":", 1)[-1]
