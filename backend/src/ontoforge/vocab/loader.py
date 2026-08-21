"""Bundled external vocabularies (FR-05, NFR-06).

The vocabularies ship inside the image, so nothing is fetched at runtime and the
tool works with the network unplugged. Each one lands in its own read-only graph
``urn:ontoforge:vocab/<name>``, well away from what the user authors (§6.1).

Fetching a vocabulary from the web stays possible, but only as an explicit act
and only from an allow-listed host (§13).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from pyoxigraph import NamedNode, Quad, RdfFormat, parse

from ontoforge.store import graphs
from ontoforge.store.store import GraphStore

DATA_DIR = Path(__file__).resolve().parent / "data"

#: Hosts a vocabulary may be fetched from when the user explicitly asks (§13).
ALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "www.w3.org",
        "w3.org",
        "schema.org",
        "xmlns.com",
        "purl.org",
        "www.dublincore.org",
        "prefix.cc",
    }
)


@dataclass(frozen=True, slots=True)
class Vocabulary:
    """One vocabulary shipped with the product."""

    name: str
    title: str
    namespace: str
    prefix: str
    filename: str
    licence: str

    @property
    def path(self) -> Path:
        return DATA_DIR / self.filename

    @property
    def rdf_format(self) -> RdfFormat:
        return RdfFormat.RDF_XML if self.path.suffix == ".rdf" else RdfFormat.TURTLE

    @property
    def graph(self) -> NamedNode:
        return graphs.vocab_graph(self.name)


#: The vocabularies §11 asks for, vendored verbatim from their publishers.
BUNDLED: tuple[Vocabulary, ...] = (
    Vocabulary(
        name="rdf",
        title="RDF",
        namespace="http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        prefix="rdf",
        filename="rdf.ttl",
        licence="W3C Software and Document Licence",
    ),
    Vocabulary(
        name="rdfs",
        title="RDF Schema",
        namespace="http://www.w3.org/2000/01/rdf-schema#",
        prefix="rdfs",
        filename="rdfs.ttl",
        licence="W3C Software and Document Licence",
    ),
    Vocabulary(
        name="owl",
        title="OWL 2",
        namespace="http://www.w3.org/2002/07/owl#",
        prefix="owl",
        filename="owl.ttl",
        licence="W3C Software and Document Licence",
    ),
    Vocabulary(
        name="skos",
        title="SKOS",
        namespace="http://www.w3.org/2004/02/skos/core#",
        prefix="skos",
        filename="skos.rdf",
        licence="W3C Software and Document Licence",
    ),
    Vocabulary(
        name="dcterms",
        title="Dublin Core Terms",
        namespace="http://purl.org/dc/terms/",
        prefix="dcterms",
        filename="dcterms.ttl",
        licence="CC BY 4.0 (DCMI)",
    ),
    Vocabulary(
        name="prov",
        title="PROV-O",
        namespace="http://www.w3.org/ns/prov#",
        prefix="prov",
        filename="prov.ttl",
        licence="W3C Software and Document Licence",
    ),
    Vocabulary(
        name="foaf",
        title="FOAF",
        namespace="http://xmlns.com/foaf/0.1/",
        prefix="foaf",
        filename="foaf.rdf",
        licence="CC BY 1.0",
    ),
    Vocabulary(
        name="schema",
        title="schema.org",
        namespace="https://schema.org/",
        prefix="schema",
        filename="schema.ttl",
        licence="CC BY-SA 3.0",
    ),
)

BY_NAME: dict[str, Vocabulary] = {vocabulary.name: vocabulary for vocabulary in BUNDLED}

#: Loaded by default: the small, universally useful ones. schema.org is large,
#: so it is opt-in even though it ships in the image.
DEFAULT_VOCABULARIES: tuple[str, ...] = ("rdf", "rdfs", "owl", "skos", "dcterms", "prov", "foaf")


class UnknownVocabularyError(LookupError):
    """Raised for a vocabulary that is not bundled."""


def get(name: str) -> Vocabulary:
    try:
        return BY_NAME[name]
    except KeyError as error:
        raise UnknownVocabularyError(
            f"{name!r} is not bundled; available: {', '.join(sorted(BY_NAME))}"
        ) from error


def read_quads(vocabulary: Vocabulary) -> list[Quad]:
    """Parse a bundled file into quads placed in its own vocabulary graph."""
    return [
        Quad(item.subject, item.predicate, item.object, vocabulary.graph)
        for item in parse(path=str(vocabulary.path), format=vocabulary.rdf_format)
    ]


def load(store: GraphStore, names: Iterable[str] = DEFAULT_VOCABULARIES) -> dict[str, int]:
    """Load the named vocabularies, replacing whatever was there before.

    Vocabulary graphs are system-owned and regenerable, so they are written
    straight to the store rather than through the change log: they are not the
    user's edits and should not fill up their undo history.
    """
    loaded: dict[str, int] = {}
    for name in names:
        vocabulary = get(name)
        store.clear_graph(vocabulary.graph)
        store.add(read_quads(vocabulary))
        # Counted from the store, not from the file: a published vocabulary may
        # state the same triple twice, and the store keeps it once.
        loaded[name] = store.count(vocabulary.graph)
    return loaded


def loaded_names(store: GraphStore) -> list[str]:
    """Which vocabularies are currently in the store."""
    return sorted(
        graphs.vocab_name(graph) for graph in store.named_graphs() if graphs.is_vocab_graph(graph)
    )


def catalogue() -> list[dict[str, str]]:
    """What the left pane offers under "external vocabularies" (§7.1)."""
    return [
        {
            "name": vocabulary.name,
            "title": vocabulary.title,
            "prefix": vocabulary.prefix,
            "namespace": vocabulary.namespace,
            "licence": vocabulary.licence,
        }
        for vocabulary in BUNDLED
    ]


def check_fetch_allowed(url: str, *, allowed: Sequence[str] | None = None) -> str:
    """Raise unless ``url`` points at an allow-listed vocabulary host (§13)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"only http(s) vocabulary URLs may be fetched, not {parsed.scheme!r}")
    hosts = frozenset(allowed) if allowed is not None else ALLOWED_HOSTS
    if parsed.hostname is None or parsed.hostname.lower() not in hosts:
        raise ValueError(
            f"{parsed.hostname!r} is not on the vocabulary allow list: {', '.join(sorted(hosts))}"
        )
    return url
