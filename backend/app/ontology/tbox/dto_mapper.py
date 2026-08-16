"""Map between v2 API schemas and OWL domain models."""

from __future__ import annotations

from app.models.schemas import (
    AnnotationSchema,
    ClassExpressionSchema,
    OwlClassCreateV2,
    OwlClassUpdateV2,
    OwlClassV2,
    OwlPropertyCreateV2,
    OwlPropertyV2,
)
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
from app.ontology.models.enums import PropertyCharacteristic, PropertyType
from app.ontology.models.owl_class import OwlClass
from app.ontology.models.owl_property import OwlProperty
from app.ontology.models.resource import Annotation
from app.storage import rdf_constants as R


def class_expression_from_schema(data: ClassExpressionSchema) -> ClassExpression:
    if data.kind == "named":
        return NamedClassExpression(iri=data.iri or "")
    if data.kind == "intersection":
        return IntersectionExpression(
            operands=[class_expression_from_schema(o) for o in data.operands]
        )
    if data.kind == "union":
        return UnionExpression(
            operands=[class_expression_from_schema(o) for o in data.operands]
        )
    if data.kind == "complement":
        return ComplementExpression(
            operand=class_expression_from_schema(data.operand) if data.operand else None
        )
    if data.kind == "oneOf":
        return OneOfExpression(individuals=data.individuals)
    if data.kind == "restriction":
        filler: ClassExpression | str | None
        if isinstance(data.filler, ClassExpressionSchema):
            filler = class_expression_from_schema(data.filler)
        else:
            filler = data.filler
        return RestrictionExpression(
            on_property=data.on_property or "",
            restriction_kind=RestrictionKind(data.restriction_kind or "someValuesFrom"),
            filler=filler,
            cardinality=data.cardinality,
        )
    raise ValueError(f"Unknown expression kind: {data.kind}")


def class_expression_to_schema(expr: ClassExpression) -> ClassExpressionSchema:
    if isinstance(expr, NamedClassExpression):
        return ClassExpressionSchema(kind="named", iri=expr.iri)
    if isinstance(expr, IntersectionExpression):
        return ClassExpressionSchema(
            kind="intersection",
            operands=[class_expression_to_schema(o) for o in expr.operands],
        )
    if isinstance(expr, UnionExpression):
        return ClassExpressionSchema(
            kind="union",
            operands=[class_expression_to_schema(o) for o in expr.operands],
        )
    if isinstance(expr, ComplementExpression):
        return ClassExpressionSchema(
            kind="complement",
            operand=class_expression_to_schema(expr.operand) if expr.operand else None,
        )
    if isinstance(expr, OneOfExpression):
        return ClassExpressionSchema(kind="oneOf", individuals=expr.individuals)
    if isinstance(expr, RestrictionExpression):
        filler_schema: ClassExpressionSchema | str | None
        if isinstance(expr.filler, ClassExpression):
            filler_schema = class_expression_to_schema(expr.filler)
        else:
            filler_schema = expr.filler
        return ClassExpressionSchema(
            kind="restriction",
            on_property=expr.on_property,
            restriction_kind=expr.restriction_kind.value,
            filler=filler_schema,
            cardinality=expr.cardinality,
        )
    raise ValueError(f"Unsupported expression: {expr}")


def subclass_ref_from_schema(item: str | ClassExpressionSchema) -> str | ClassExpression:
    if isinstance(item, str):
        return R.class_uri(item)
    return class_expression_from_schema(item)


def subclass_ref_to_schema(item: str | ClassExpression) -> str | ClassExpressionSchema:
    if isinstance(item, str):
        return R.class_id_from_uri(item)
    return class_expression_to_schema(item)


def owl_class_to_v2(cls: OwlClass, dto_labels: list[str] | None = None) -> OwlClassV2:
    labels = dto_labels or []
    return OwlClassV2(
        iri=cls.iri,
        id=R.class_id_from_uri(cls.iri),
        labels=labels,
        subclass_of=[subclass_ref_to_schema(s) for s in cls.subclass_of],
        equivalent_class=[class_expression_to_schema(e) for e in cls.equivalent_class],
        disjoint_with=[subclass_ref_to_schema(d) for d in cls.disjoint_with],
        annotations=[
            AnnotationSchema(
                property=a.property,
                value=a.value,
                language=a.language,
                datatype=a.datatype,
            )
            for a in cls.annotations
        ],
    )


def owl_property_to_v2(prop: OwlProperty, dto: OwlPropertyV2 | None = None) -> OwlPropertyV2:
    local_id = R.local_name(prop.iri).split(":", 1)[-1]
    domain = [
        R.class_id_from_uri(d) if d.startswith(R.KG) else d
        for d in prop.domain
        if isinstance(d, str)
    ]
    range_vals = []
    for r in prop.range_iris:
        if isinstance(r, str):
            if r.startswith(R.XSD):
                range_vals.append(r.rsplit("#", 1)[-1] if "#" in r else r.rsplit(":", 1)[-1])
            elif r.startswith(R.KG):
                range_vals.append(R.class_id_from_uri(r))
            else:
                range_vals.append(r)
    return OwlPropertyV2(
        iri=prop.iri,
        id=local_id,
        label=dto.label if dto else local_id,
        description=dto.description if dto else "",
        property_type=prop.property_type.value,
        domain=domain,
        range=range_vals,
        sub_property_of=[R.local_name(s).split(":", 1)[-1] for s in prop.sub_property_of],
        inverse_of=R.local_name(prop.inverse_of).split(":", 1)[-1] if prop.inverse_of else None,
        characteristics=[c.value for c in prop.characteristics],
        editor_required=prop.editor_required,
        aliases=dto.aliases if dto else [],
    )


def create_v2_class(data: OwlClassCreateV2) -> OwlClass:
    return OwlClass(
        iri=R.class_uri(data.id),
        types=[R.OWL_CLASS],
        subclass_of=[subclass_ref_from_schema(s) for s in data.subclass_of],
        equivalent_class=[class_expression_from_schema(e) for e in data.equivalent_class],
        disjoint_with=[subclass_ref_from_schema(d) for d in data.disjoint_with],
        annotations=_build_annotations(data.label, data.description, data.aliases, data.examples),
    )


def create_v2_property(data: OwlPropertyCreateV2) -> OwlProperty:
    prop_type = PropertyType(data.property_type)
    uri = (
        R.relationship_uri(data.id)
        if prop_type == PropertyType.OBJECT
        else R.property_uri(data.id)
    )
    type_iri = {
        PropertyType.OBJECT: R.OWL_OBJECT_PROPERTY,
        PropertyType.DATATYPE: R.OWL_DATATYPE_PROPERTY,
        PropertyType.ANNOTATION: R.OWL_ANNOTATION_PROPERTY,
    }[prop_type]
    characteristics = {PropertyCharacteristic(c) for c in data.characteristics}
    return OwlProperty(
        iri=uri,
        types=[type_iri],
        property_type=prop_type,
        domain=[R.class_uri(d) for d in data.domain],
        range_iris=[_resolve_range(r) for r in data.range],
        sub_property_of=[
            R.relationship_uri(s) if prop_type == PropertyType.OBJECT else R.property_uri(s)
            for s in data.sub_property_of
        ],
        inverse_of=R.relationship_uri(data.inverse_of) if data.inverse_of else None,
        characteristics=characteristics,
        editor_required=data.editor_required,
        annotations=_build_annotations(data.label, data.description, data.aliases, []),
    )


def update_v2_class(existing: OwlClass, data: OwlClassUpdateV2) -> OwlClass:
    label = _label_from_annotations(existing)
    description = _comment_from_annotations(existing)
    aliases = _aliases_from_annotations(existing)
    examples = _examples_from_annotations(existing)
    return OwlClass(
        iri=existing.iri,
        types=[R.OWL_CLASS],
        subclass_of=(
            [subclass_ref_from_schema(s) for s in data.subclass_of]
            if data.subclass_of is not None
            else existing.subclass_of
        ),
        equivalent_class=(
            [class_expression_from_schema(e) for e in data.equivalent_class]
            if data.equivalent_class is not None
            else existing.equivalent_class
        ),
        disjoint_with=(
            [subclass_ref_from_schema(d) for d in data.disjoint_with]
            if data.disjoint_with is not None
            else existing.disjoint_with
        ),
        annotations=_build_annotations(
            data.label if data.label is not None else label,
            data.description if data.description is not None else description,
            data.aliases if data.aliases is not None else aliases,
            data.examples if data.examples is not None else examples,
        ),
    )


def _resolve_range(range_value: str) -> str:
    if range_value.startswith("xsd:"):
        return f"{R.XSD}{range_value[4:]}"
    if range_value.startswith(R.XSD):
        return range_value
    return R.class_uri(range_value)


def _build_annotations(
    label: str,
    description: str,
    aliases: list[str],
    examples: list[str],
) -> list[Annotation]:
    anns: list[Annotation] = []
    if label:
        anns.append(Annotation(property=R.RDFS_LABEL, value=label))
    if description:
        anns.append(Annotation(property=R.RDFS_COMMENT, value=description))
    for alias in aliases:
        anns.append(Annotation(property=R.KG_ALIAS, value=alias))
    for example in examples:
        anns.append(Annotation(property=R.KG_EXAMPLE, value=example))
    return anns


def _label_from_annotations(cls: OwlClass) -> str:
    for ann in cls.annotations:
        if ann.property == R.RDFS_LABEL:
            return ann.value
    return ""


def _comment_from_annotations(cls: OwlClass) -> str:
    for ann in cls.annotations:
        if ann.property == R.RDFS_COMMENT:
            return ann.value
    return ""


def _aliases_from_annotations(cls: OwlClass) -> list[str]:
    return [a.value for a in cls.annotations if a.property == R.KG_ALIAS]


def _examples_from_annotations(cls: OwlClass) -> list[str]:
    return [a.value for a in cls.annotations if a.property == R.KG_EXAMPLE]
