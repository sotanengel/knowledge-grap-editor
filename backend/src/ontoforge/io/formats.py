"""The formats OntoForge reads and writes (§11).

Exports go beyond RDF on purpose: GraphML for Gephi and yEd, node/edge CSV for
Neo4j, Mermaid for pasting into documentation. Being able to walk away with the
data is what keeps the tool from locking anyone in (P3).
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath

from pyoxigraph import RdfFormat


class ImportFormat(StrEnum):
    """What ``POST /import`` accepts."""

    TURTLE = "turtle"
    TRIG = "trig"
    NTRIPLES = "ntriples"
    NQUADS = "nquads"
    RDFXML = "rdfxml"
    JSONLD = "jsonld"
    CSV = "csv"


class ExportFormat(StrEnum):
    """What ``GET /export`` produces."""

    TURTLE = "turtle"
    TRIG = "trig"
    NTRIPLES = "ntriples"
    NQUADS = "nquads"
    RDFXML = "rdfxml"
    JSONLD = "jsonld"
    GRAPHML = "graphml"
    CSV = "csv"
    MERMAID = "mermaid"


#: Formats that map straight onto a pyoxigraph serialisation.
RDF_FORMATS: dict[str, RdfFormat] = {
    "turtle": RdfFormat.TURTLE,
    "trig": RdfFormat.TRIG,
    "ntriples": RdfFormat.N_TRIPLES,
    "nquads": RdfFormat.N_QUADS,
    "rdfxml": RdfFormat.RDF_XML,
    "jsonld": RdfFormat.JSON_LD,
}

#: Formats that carry graph names, so they can be loaded as a whole dataset.
DATASET_FORMATS = frozenset({"trig", "nquads"})

_EXTENSIONS: dict[str, str] = {
    ".ttl": "turtle",
    ".turtle": "turtle",
    ".trig": "trig",
    ".nt": "ntriples",
    ".ntriples": "ntriples",
    ".nq": "nquads",
    ".nquads": "nquads",
    ".rdf": "rdfxml",
    ".xml": "rdfxml",
    ".owl": "rdfxml",
    ".jsonld": "jsonld",
    ".json": "jsonld",
    ".csv": "csv",
    ".tsv": "csv",
}

MEDIA_TYPES: dict[str, str] = {
    "turtle": "text/turtle",
    "trig": "application/trig",
    "ntriples": "application/n-triples",
    "nquads": "application/n-quads",
    "rdfxml": "application/rdf+xml",
    "jsonld": "application/ld+json",
    "graphml": "application/graphml+xml",
    "csv": "application/zip",
    "mermaid": "text/vnd.mermaid",
}

FILE_EXTENSIONS: dict[str, str] = {
    "turtle": "ttl",
    "trig": "trig",
    "ntriples": "nt",
    "nquads": "nq",
    "rdfxml": "rdf",
    "jsonld": "jsonld",
    "graphml": "graphml",
    "csv": "zip",
    "mermaid": "mmd",
}


def format_for_filename(filename: str) -> ImportFormat | None:
    """Guess the import format from a file name, or ``None`` if it is unknown."""
    suffix = PurePosixPath(filename).suffix.lower()
    name = _EXTENSIONS.get(suffix)
    return ImportFormat(name) if name is not None else None


def rdf_format(name: str) -> RdfFormat | None:
    """The pyoxigraph serialisation for ``name``, if it has one."""
    return RDF_FORMATS.get(name)


def is_dataset_format(name: str) -> bool:
    """Whether the format records graph names alongside triples."""
    return name in DATASET_FORMATS


def media_type(name: str) -> str:
    return MEDIA_TYPES.get(name, "application/octet-stream")


def file_extension(name: str) -> str:
    return FILE_EXTENSIONS.get(name, "dat")
