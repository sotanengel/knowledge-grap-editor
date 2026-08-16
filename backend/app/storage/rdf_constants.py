"""RDF namespace constants and URI helpers."""

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OWL = "http://www.w3.org/2002/07/owl#"
XSD = "http://www.w3.org/2001/XMLSchema#"
KG = "urn:kg:"

XSD_STRING = f"{XSD}string"
XSD_BOOLEAN = f"{XSD}boolean"
XSD_INTEGER = f"{XSD}integer"
XSD_DECIMAL = f"{XSD}decimal"
XSD_FLOAT = f"{XSD}float"
XSD_DOUBLE = f"{XSD}double"
XSD_DATE = f"{XSD}date"
XSD_DATETIME = f"{XSD}dateTime"
XSD_TIME = f"{XSD}time"
XSD_ANYURI = f"{XSD}anyURI"

RDF_TYPE = f"{RDF}type"
RDFS_LABEL = f"{RDFS}label"
RDFS_COMMENT = f"{RDFS}comment"
RDFS_DOMAIN = f"{RDFS}domain"
RDFS_RANGE = f"{RDFS}range"
RDFS_SUBCLASS_OF = f"{RDFS}subClassOf"
OWL_CLASS = f"{OWL}Class"
OWL_OBJECT_PROPERTY = f"{OWL}ObjectProperty"
OWL_DATATYPE_PROPERTY = f"{OWL}DatatypeProperty"
OWL_ANNOTATION_PROPERTY = f"{OWL}AnnotationProperty"
OWL_RESTRICTION = f"{OWL}Restriction"
OWL_ON_PROPERTY = f"{OWL}onProperty"
OWL_SOME_VALUES_FROM = f"{OWL}someValuesFrom"
OWL_ALL_VALUES_FROM = f"{OWL}allValuesFrom"
OWL_HAS_VALUE = f"{OWL}hasValue"
OWL_HAS_SELF = f"{OWL}hasSelf"
OWL_CARDINALITY = f"{OWL}cardinality"
OWL_MIN_CARDINALITY = f"{OWL}minCardinality"
OWL_MAX_CARDINALITY = f"{OWL}maxCardinality"
OWL_INVERSE_OF = f"{OWL}inverseOf"
OWL_EQUIVALENT_CLASS = f"{OWL}equivalentClass"
OWL_DISJOINT_WITH = f"{OWL}disjointWith"
OWL_SAME_AS = f"{OWL}sameAs"
OWL_DIFFERENT_FROM = f"{OWL}differentFrom"
KG_ALIAS = f"{KG}alias"
KG_EXAMPLE = f"{KG}example"
KG_REQUIRED = f"{KG}required"
KG_EDITOR_REQUIRED = f"{KG}editorRequired"
KG_CREATED_AT = f"{KG}createdAt"
KG_UPDATED_AT = f"{KG}updatedAt"
KG_EDGE_ID = f"{KG}edgeId"


def node_uri(node_id: str) -> str:
    return f"{KG}node:{node_id}"


def class_uri(class_id: str) -> str:
    return f"{KG}class:{class_id}"


def property_uri(prop_id: str) -> str:
    return f"{KG}property:{prop_id}"


def relationship_uri(rel_id: str) -> str:
    return f"{KG}relationship:{rel_id}"


def edge_uri(edge_id: str) -> str:
    return f"{KG}edge:{edge_id}"


def class_id_from_uri(uri: str) -> str:
    prefix = f"{KG}class:"
    if uri.startswith(prefix):
        return uri[len(prefix) :]
    if uri.startswith(KG):
        return uri.replace(KG, "")
    return uri.split(":")[-1]


def local_name(uri: str) -> str:
    for prefix in (f"{KG}node:", f"{KG}class:", f"{KG}property:", f"{KG}relationship:"):
        if uri.startswith(prefix):
            return uri[len(prefix) :]
    if "#" in uri:
        return uri.rsplit("#", 1)[-1]
    return uri.rsplit(":", 1)[-1]
