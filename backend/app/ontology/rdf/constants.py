"""Extended RDF / OWL constants."""

from app.storage import rdf_constants as R

# Re-export base constants
RDF = R.RDF
RDFS = R.RDFS
OWL = R.OWL
XSD = R.XSD
KG = R.KG
RDF_TYPE = R.RDF_TYPE
RDFS_LABEL = R.RDFS_LABEL
RDFS_COMMENT = R.RDFS_COMMENT
RDFS_DOMAIN = R.RDFS_DOMAIN
RDFS_RANGE = R.RDFS_RANGE
RDFS_SUBCLASS_OF = R.RDFS_SUBCLASS_OF

# OWL class types
OWL_CLASS = R.OWL_CLASS
OWL_THING = f"{OWL}Thing"
OWL_NOTHING = f"{OWL}Nothing"

# OWL property types
OWL_OBJECT_PROPERTY = R.OWL_OBJECT_PROPERTY
OWL_DATATYPE_PROPERTY = R.OWL_DATATYPE_PROPERTY
OWL_ANNOTATION_PROPERTY = R.OWL_ANNOTATION_PROPERTY

# OWL class axioms
OWL_EQUIVALENT_CLASS = f"{OWL}equivalentClass"
OWL_DISJOINT_WITH = f"{OWL}disjointWith"

# OWL property axioms
OWL_INVERSE_OF = f"{OWL}inverseOf"
RDFS_SUB_PROPERTY_OF = f"{RDFS}subPropertyOf"

# OWL class expression
OWL_INTERSECTION_OF = f"{OWL}intersectionOf"
OWL_UNION_OF = f"{OWL}unionOf"
OWL_COMPLEMENT_OF = f"{OWL}complementOf"
OWL_ONE_OF = f"{OWL}oneOf"

# OWL restrictions
OWL_RESTRICTION = f"{OWL}Restriction"
OWL_ON_PROPERTY = f"{OWL}onProperty"
OWL_SOME_VALUES_FROM = f"{OWL}someValuesFrom"
OWL_ALL_VALUES_FROM = f"{OWL}allValuesFrom"
OWL_HAS_VALUE = f"{OWL}hasValue"
OWL_HAS_SELF = f"{OWL}hasSelf"
OWL_CARDINALITY = f"{OWL}cardinality"
OWL_MIN_CARDINALITY = f"{OWL}minCardinality"
OWL_MAX_CARDINALITY = f"{OWL}maxCardinality"
OWL_QUALIFIED_CARDINALITY = f"{OWL}qualifiedCardinality"
OWL_ON_CLASS = f"{OWL}onClass"
OWL_ON_DATA_RANGE = f"{OWL}onDataRange"

# Individual axioms
OWL_SAME_AS = f"{OWL}sameAs"
OWL_DIFFERENT_FROM = f"{OWL}differentFrom"
OWL_ALL_DIFFERENT = f"{OWL}AllDifferent"
OWL_DISTINCT_MEMBERS = f"{OWL}distinctMembers"

# Annotation
RDFS_SEE_ALSO = f"{RDFS}seeAlso"

# KG editor-specific annotation properties
KG_ALIAS = R.KG_ALIAS
KG_EXAMPLE = R.KG_EXAMPLE
KG_EDITOR_REQUIRED = R.KG_EDITOR_REQUIRED
KG_REQUIRED = R.KG_REQUIRED  # legacy v1

# Annotation property IRIs treated as non-logical
ANNOTATION_PROPERTIES = {
    R.RDFS_LABEL,
    R.RDFS_COMMENT,
    RDFS_SEE_ALSO,
    KG_ALIAS,
    KG_EXAMPLE,
    KG_EDITOR_REQUIRED,
    KG_REQUIRED,
}

RESTRICTION_PREDICATE_MAP = {
    "someValuesFrom": OWL_SOME_VALUES_FROM,
    "allValuesFrom": OWL_ALL_VALUES_FROM,
    "hasValue": OWL_HAS_VALUE,
    "hasSelf": OWL_HAS_SELF,
    "cardinality": OWL_CARDINALITY,
    "minCardinality": OWL_MIN_CARDINALITY,
    "maxCardinality": OWL_MAX_CARDINALITY,
}
