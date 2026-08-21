"""JSON-LD 1.1 documents, the exchange format for the API (§4.2).

Front-end code can treat these as ordinary JSON; anything that cares can use
``@context`` to turn them back into RDF. IRIs are kept expanded so a client
never has to resolve a prefix to know what it is looking at, while the context
still travels with the document for the tools that want it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pyoxigraph import Literal, NamedNode, Quad

from ontoforge.literals import term_to_json
from ontoforge.namespaces import LABEL_PREDICATES, PREFIXES, RDF_TYPE, RDFS_LABEL

Context = dict[str, str]


def build_context(base_iri: str) -> Context:
    """The preset prefixes plus the two namespaces this project mints into."""
    context: Context = dict(PREFIXES)
    context["ont"] = f"{base_iri}ont#"
    context["id"] = f"{base_iri}id/"
    return context


def expand_iri(term: str, context: Context) -> str:
    """Turn ``ont:Person`` into a full IRI; absolute IRIs pass through."""
    if "://" in term or term.startswith("urn:"):
        return term
    prefix, separator, local = term.partition(":")
    if separator and prefix in context:
        return f"{context[prefix]}{local}"
    return term


def compact_iri(iri: str, context: Context) -> str:
    """The shortest prefixed name for ``iri``, or the IRI itself."""
    best: str | None = None
    best_length = -1
    for prefix, namespace in context.items():
        if iri.startswith(namespace) and len(namespace) > best_length:
            best = f"{prefix}:{iri.removeprefix(namespace)}"
            best_length = len(namespace)
    return best if best is not None else iri


def label_term_of(quads: Iterable[Quad]) -> Literal | None:
    """The most specific label literal among ``quads`` (skos:prefLabel beats rdfs:label)."""
    found: dict[NamedNode, Literal] = {}
    for quad in quads:
        if quad.predicate in LABEL_PREDICATES and isinstance(quad.object, Literal):
            found.setdefault(quad.predicate, quad.object)
    for predicate in LABEL_PREDICATES:
        if predicate in found:
            return found[predicate]
    return None


def label_of(quads: Iterable[Quad]) -> str | None:
    """The plain text of the most specific label among ``quads``."""
    term = label_term_of(quads)
    return None if term is None else term.value


def node_document(
    subject: str,
    quads: Iterable[Quad],
    *,
    labels: Mapping[str, Literal] | None = None,
) -> dict[str, Any]:
    """One JSON-LD node object built from the quads describing ``subject``.

    ``labels`` lets referenced IRIs carry their own ``rdfs:label`` so a reader --
    a person or an LLM -- never sees a bare IRI without knowing what it names
    (§9.5).
    """
    document: dict[str, Any] = {"@id": subject}
    types: list[str] = []
    properties: dict[str, list[Any]] = {}

    for quad in quads:
        if quad.predicate == RDF_TYPE and isinstance(quad.object, NamedNode):
            types.append(quad.object.value)
            continue
        value = term_to_json(quad.object)
        if labels and "@id" in value:
            label = labels.get(value["@id"])
            if label is not None:
                value = {**value, RDFS_LABEL.value: [term_to_json(label)]}
        properties.setdefault(quad.predicate.value, []).append(value)

    if types:
        document["@type"] = types
    document.update(properties)
    return document


def with_context(document: dict[str, Any], context: Context) -> dict[str, Any]:
    """Prepend ``@context`` so it reads first in the serialised JSON."""
    return {"@context": context, **document}


def graph_document(
    nodes: Iterable[dict[str, Any]],
    context: Context,
    *,
    root: str | None = None,
) -> dict[str, Any]:
    """A ``@graph`` document, used when a request pulls in a neighbourhood."""
    document: dict[str, Any] = {"@context": context, "@graph": list(nodes)}
    if root is not None:
        document["@id"] = root
    return document
