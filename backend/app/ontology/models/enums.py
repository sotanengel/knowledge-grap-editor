from enum import StrEnum


class PropertyType(StrEnum):
    OBJECT = "ObjectProperty"
    DATATYPE = "DatatypeProperty"
    ANNOTATION = "AnnotationProperty"


class PropertyCharacteristic(StrEnum):
    FUNCTIONAL = "FunctionalProperty"
    INVERSE_FUNCTIONAL = "InverseFunctionalProperty"
    TRANSITIVE = "TransitiveProperty"
    SYMMETRIC = "SymmetricProperty"
    ASYMMETRIC = "AsymmetricProperty"
    REFLEXIVE = "ReflexiveProperty"
    IRREFLEXIVE = "IrreflexiveProperty"


CHARACTERISTIC_IRIS: dict[PropertyCharacteristic, str] = {
    PropertyCharacteristic.FUNCTIONAL: "http://www.w3.org/2002/07/owl#FunctionalProperty",
    PropertyCharacteristic.INVERSE_FUNCTIONAL: (
        "http://www.w3.org/2002/07/owl#InverseFunctionalProperty"
    ),
    PropertyCharacteristic.TRANSITIVE: "http://www.w3.org/2002/07/owl#TransitiveProperty",
    PropertyCharacteristic.SYMMETRIC: "http://www.w3.org/2002/07/owl#SymmetricProperty",
    PropertyCharacteristic.ASYMMETRIC: "http://www.w3.org/2002/07/owl#AsymmetricProperty",
    PropertyCharacteristic.REFLEXIVE: "http://www.w3.org/2002/07/owl#ReflexiveProperty",
    PropertyCharacteristic.IRREFLEXIVE: "http://www.w3.org/2002/07/owl#IrreflexiveProperty",
}

IRI_TO_CHARACTERISTIC = {v: k for k, v in CHARACTERISTIC_IRIS.items()}
