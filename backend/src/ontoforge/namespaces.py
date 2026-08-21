"""Well-known vocabulary IRIs and the prefixes the UI hides behind display names (§4.3)."""

from __future__ import annotations

from pyoxigraph import NamedNode

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OWL = "http://www.w3.org/2002/07/owl#"
XSD = "http://www.w3.org/2001/XMLSchema#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
SH = "http://www.w3.org/ns/shacl#"
PROV = "http://www.w3.org/ns/prov#"
DCTERMS = "http://purl.org/dc/terms/"
FOAF = "http://xmlns.com/foaf/0.1/"
SCHEMA = "https://schema.org/"
#: OntoForge's own terms (edge confidence, assertion metadata).
ONTF = "https://ontoforge.dev/ns#"

#: Prefixes preset for every project. Users never type these (§4.3).
PREFIXES: dict[str, str] = {
    "rdf": RDF,
    "rdfs": RDFS,
    "owl": OWL,
    "xsd": XSD,
    "skos": SKOS,
    "sh": SH,
    "prov": PROV,
    "dcterms": DCTERMS,
    "foaf": FOAF,
    "schema": SCHEMA,
    "ontf": ONTF,
}

RDF_TYPE = NamedNode(f"{RDF}type")
RDF_PROPERTY = NamedNode(f"{RDF}Property")
#: RDF 1.2 reification: a reifier node points at the triple term it describes.
RDF_REIFIES = NamedNode(f"{RDF}reifies")

RDFS_CLASS = NamedNode(f"{RDFS}Class")
RDFS_LABEL = NamedNode(f"{RDFS}label")
RDFS_COMMENT = NamedNode(f"{RDFS}comment")
RDFS_SUBCLASS_OF = NamedNode(f"{RDFS}subClassOf")
RDFS_SUBPROPERTY_OF = NamedNode(f"{RDFS}subPropertyOf")
RDFS_DOMAIN = NamedNode(f"{RDFS}domain")
RDFS_RANGE = NamedNode(f"{RDFS}range")

OWL_CLASS = NamedNode(f"{OWL}Class")
OWL_OBJECT_PROPERTY = NamedNode(f"{OWL}ObjectProperty")
OWL_DATATYPE_PROPERTY = NamedNode(f"{OWL}DatatypeProperty")

SKOS_PREF_LABEL = NamedNode(f"{SKOS}prefLabel")

PROV_WAS_DERIVED_FROM = NamedNode(f"{PROV}wasDerivedFrom")

ONTF_CONFIDENCE = NamedNode(f"{ONTF}confidence")
ONTF_ASSERTED_AT = NamedNode(f"{ONTF}assertedAt")
ONTF_ASSERTED_BY = NamedNode(f"{ONTF}assertedBy")
ONTF_X = NamedNode(f"{ONTF}x")
ONTF_Y = NamedNode(f"{ONTF}y")

#: Predicates that carry a human-readable name, most specific first.
LABEL_PREDICATES = (SKOS_PREF_LABEL, RDFS_LABEL)
#: Predicates the class tree is built from.
CLASS_TYPES = (OWL_CLASS, RDFS_CLASS)
#: Predicates the property list is built from.
PROPERTY_TYPES = (OWL_OBJECT_PROPERTY, OWL_DATATYPE_PROPERTY, RDF_PROPERTY)
