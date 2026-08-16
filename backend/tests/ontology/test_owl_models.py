"""Tests for OWL domain models."""

from app.ontology.models.enums import PropertyCharacteristic, PropertyType
from app.ontology.models.literal import LiteralValue
from app.ontology.models.owl_class import OwlClass
from app.ontology.models.owl_property import OwlProperty
from app.ontology.models.resource import Annotation, Resource
from app.ontology.models.triple import Triple, TripleSource
from app.storage import rdf_constants as R


def test_resource_model():
    res = Resource(iri=R.class_uri("Person"), types=[R.OWL_CLASS])
    assert res.iri == R.class_uri("Person")
    assert R.OWL_CLASS in res.types


def test_owl_class_model():
    cls = OwlClass(
        iri=R.class_uri("Person"),
        types=[R.OWL_CLASS],
        subclass_of=[R.class_uri("Entity")],
        annotations=[Annotation(property=R.RDFS_LABEL, value="Person", language="en")],
    )
    assert cls.subclass_of == [R.class_uri("Entity")]


def test_owl_property_with_characteristics():
    prop = OwlProperty(
        iri=R.property_uri("name"),
        types=[R.OWL_DATATYPE_PROPERTY],
        property_type=PropertyType.DATATYPE,
        range_iris=[R.XSD_STRING],
        characteristics={PropertyCharacteristic.FUNCTIONAL},
    )
    assert prop.property_type == PropertyType.DATATYPE
    assert PropertyCharacteristic.FUNCTIONAL in prop.characteristics


def test_literal_value():
    lit = LiteralValue(lexical="hello", datatype=R.XSD_STRING)
    assert lit.lexical == "hello"
    assert lit.datatype == R.XSD_STRING


def test_triple_source():
    t = Triple(
        subject=R.node_uri("alice"),
        predicate=R.property_uri("name"),
        object=R.node_uri("alice"),
        source=TripleSource.EXPLICIT,
    )
    assert t.source == TripleSource.EXPLICIT
    assert not t.is_annotation
