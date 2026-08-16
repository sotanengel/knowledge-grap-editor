"""Tests for OWL ClassExpression AST and RDF round-trip."""

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
from app.ontology.rdf.mapper import RdfMapper
from app.storage import rdf_constants as R


def test_named_class_expression():
    expr = NamedClassExpression(iri=R.class_uri("Person"))
    assert expr.kind == "named"
    assert expr.iri == R.class_uri("Person")


def test_intersection_expression():
    expr = IntersectionExpression(
        operands=[
            NamedClassExpression(iri=R.class_uri("Person")),
            RestrictionExpression(
                on_property=R.relationship_uri("hasChild"),
                restriction_kind=RestrictionKind.SOME,
                filler=NamedClassExpression(iri=R.class_uri("Person")),
            ),
        ]
    )
    assert expr.kind == "intersection"
    assert len(expr.operands) == 2


def test_restriction_some_values_from():
    expr = RestrictionExpression(
        on_property=R.relationship_uri("hasChild"),
        restriction_kind=RestrictionKind.SOME,
        filler=NamedClassExpression(iri=R.class_uri("Person")),
    )
    assert expr.kind == "restriction"
    assert expr.restriction_kind == RestrictionKind.SOME


def test_class_expression_to_dict_round_trip():
    expr = UnionExpression(
        operands=[
            NamedClassExpression(iri=R.class_uri("Mother")),
            NamedClassExpression(iri=R.class_uri("Father")),
        ]
    )
    data = expr.to_dict()
    restored = ClassExpression.from_dict(data)
    assert restored.kind == "union"
    assert len(restored.operands) == 2  # type: ignore[attr-defined]


def test_complement_expression():
    expr = ComplementExpression(
        operand=NamedClassExpression(iri=R.class_uri("Minor"))
    )
    data = expr.to_dict()
    restored = ClassExpression.from_dict(data)
    assert restored.kind == "complement"


def test_one_of_expression():
    expr = OneOfExpression(
        individuals=[R.node_uri("red"), R.node_uri("blue"), R.node_uri("green")]
    )
    assert expr.kind == "oneOf"
    assert len(expr.individuals) == 3


def test_mapper_serializes_named_class_to_triples():
    mapper = RdfMapper()
    expr = NamedClassExpression(iri=R.class_uri("Person"))
    triples = mapper.class_expression_to_triples(expr, blank_node="_:parent")
    assert any(t.predicate == R.RDF_TYPE and t.object == R.OWL_CLASS for t in triples)


def test_mapper_serializes_restriction():
    mapper = RdfMapper()
    expr = RestrictionExpression(
        on_property=R.relationship_uri("hasChild"),
        restriction_kind=RestrictionKind.SOME,
        filler=NamedClassExpression(iri=R.class_uri("Person")),
    )
    triples = mapper.class_expression_to_triples(expr, blank_node="_:r1")
    predicates = {t.predicate for t in triples}
    assert R.OWL_RESTRICTION in {t.object for t in triples if t.predicate == R.RDF_TYPE}
    assert R.OWL_ON_PROPERTY in predicates
    assert R.OWL_SOME_VALUES_FROM in predicates
