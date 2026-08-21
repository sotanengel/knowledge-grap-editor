"""Instance CRUD (§8, FR-01 to FR-04).

The user types a label and picks a type; everything else -- minting the IRI,
choosing the literal datatype, attaching the language tag -- happens here so it
never has to surface in the interface (P1).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pyoxigraph import BlankNode, Literal, NamedNode, Quad, Triple

from ontoforge.jsonld import (
    build_context,
    expand_iri,
    graph_document,
    label_term_of,
    node_document,
    with_context,
)
from ontoforge.literals import make_literal, term_from_json
from ontoforge.namespaces import RDF_TYPE, RDFS_COMMENT, RDFS_LABEL
from ontoforge.runtime import Runtime
from ontoforge.store import graphs

#: Labels are stored with a language tag; Japanese is the default (§15.2 Q10).
DEFAULT_LANGUAGE = "ja"

PropertyMap = Mapping[str, Any]


class EntityNotFoundError(LookupError):
    """Raised when an IRI names nothing in the graph."""


class EntityService:
    """Create, read, update and delete instances in ``urn:ontoforge:data``."""

    def __init__(self, runtime: Runtime, *, graph: NamedNode = graphs.DATA) -> None:
        self.runtime = runtime
        self.graph = graph
        self.context = build_context(runtime.settings.base_iri)

    # ------------------------------------------------------------------ create

    def create(
        self,
        *,
        label: str,
        types: Iterable[str] = (),
        properties: PropertyMap | None = None,
        comment: str | None = None,
        language: str = DEFAULT_LANGUAGE,
        actor: str = "user",
    ) -> dict[str, Any]:
        """Mint an instance IRI and assert what is known about it."""
        cleaned = label.strip()
        if not cleaned:
            raise ValueError("label must not be empty")

        subject = self.runtime.minter.new_instance()
        quads = [Quad(subject, RDFS_LABEL, make_literal(cleaned, language=language), self.graph)]
        if comment:
            quads.append(
                Quad(subject, RDFS_COMMENT, make_literal(comment, language=language), self.graph)
            )
        quads.extend(
            Quad(subject, RDF_TYPE, NamedNode(self._expand(type_iri)), self.graph)
            for type_iri in types
        )
        quads.extend(self._property_quads(subject, properties or {}))

        self.runtime.write(additions=quads, actor=actor)
        return self.get(subject.value)

    # ------------------------------------------------------------------ read

    def get(self, iri: str, *, depth: int = 1) -> dict[str, Any]:
        """The CBD of ``iri``, optionally with its neighbourhood (§8)."""
        subject = NamedNode(self._expand(iri))
        quads = self.runtime.store.describe(subject, depth=depth)
        if not quads:
            raise EntityNotFoundError(iri)

        if depth <= 1:
            return with_context(
                node_document(subject.value, quads, labels=self._labels_for(quads)),
                self.context,
            )

        by_subject: dict[str, list[Quad]] = {}
        for quad in quads:
            if isinstance(quad.subject, NamedNode):
                by_subject.setdefault(quad.subject.value, []).append(quad)
        labels = self._labels_for(quads)
        nodes = [node_document(node, group, labels=labels) for node, group in by_subject.items()]
        return graph_document(nodes, self.context, root=subject.value)

    def search(
        self,
        *,
        query: str = "",
        type_iri: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Label search, backed by the FTS index (FR-08)."""
        hits = self.runtime.search.search(
            query,
            type_iri=self._expand(type_iri) if type_iri else None,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "@id": hit.iri,
                "@type": list(hit.types),
                RDFS_LABEL.value: [{"@value": hit.label, "@language": DEFAULT_LANGUAGE}],
                **({RDFS_COMMENT.value: [{"@value": hit.comment}]} if hit.comment else {}),
            }
            for hit in hits
        ]

    # ------------------------------------------------------------------ update

    def patch(
        self,
        iri: str,
        *,
        add: PropertyMap | None = None,
        remove: PropertyMap | None = None,
        label: str | None = None,
        comment: str | None = None,
        language: str = DEFAULT_LANGUAGE,
        actor: str = "user",
    ) -> dict[str, Any]:
        """Add and remove triples. The IRI never moves -- a rename is a label change."""
        subject = NamedNode(self._expand(iri))
        existing = list(self.runtime.store.quads_for_pattern(subject, None, None, self.graph))
        if not existing:
            raise EntityNotFoundError(iri)

        additions = list(self._property_quads(subject, add or {}))
        deletions = list(self._property_quads(subject, remove or {}))

        for predicate, text in ((RDFS_LABEL, label), (RDFS_COMMENT, comment)):
            if text is None:
                continue
            deletions.extend(quad for quad in existing if quad.predicate == predicate)
            additions.append(
                Quad(subject, predicate, make_literal(text.strip(), language=language), self.graph)
            )

        self.runtime.write(additions=additions, deletions=deletions, actor=actor)
        return self.get(subject.value)

    # ------------------------------------------------------------------ delete

    def delete(self, iri: str, *, actor: str = "user") -> int:
        """Remove the node and every triple that mentions it (§8)."""
        subject = NamedNode(self._expand(iri))
        outgoing = list(self.runtime.store.quads_for_pattern(subject, None, None, None))
        incoming = list(self.runtime.store.quads_for_pattern(None, None, subject, None))
        doomed = list({*outgoing, *incoming})
        if not doomed:
            raise EntityNotFoundError(iri)

        self.runtime.write(deletions=doomed, actor=actor)
        return len(doomed)

    # ------------------------------------------------------------------ helpers

    def _expand(self, term: str) -> str:
        return expand_iri(term, self.context)

    def _property_quads(self, subject: NamedNode, properties: PropertyMap) -> list[Quad]:
        """Turn ``{predicate: value-or-values}`` into quads."""
        quads: list[Quad] = []
        for raw_predicate, raw_value in properties.items():
            predicate = NamedNode(self._expand(raw_predicate))
            values = raw_value if isinstance(raw_value, list) else [raw_value]
            for value in values:
                quads.append(Quad(subject, predicate, self._object(predicate, value), self.graph))
        return quads

    def _object(self, predicate: NamedNode, value: Any) -> Any:
        term = term_from_json(value)
        if predicate == RDF_TYPE and not isinstance(term, NamedNode | BlankNode | Triple):
            # A type given as a bare string is still a type, not a literal.
            return NamedNode(self._expand(term.value))
        if isinstance(term, NamedNode):
            return NamedNode(self._expand(term.value))
        return term

    def _labels_for(self, quads: Iterable[Quad]) -> dict[str, Literal]:
        """Labels of every IRI referenced as an object, so no bare IRI is returned."""
        referenced = {quad.object for quad in quads if isinstance(quad.object, NamedNode)} - {
            quad.subject for quad in quads if isinstance(quad.subject, NamedNode)
        }
        labels: dict[str, Literal] = {}
        for node in referenced:
            found = label_term_of(self.runtime.store.quads_for_pattern(node, None, None, None))
            if found is not None:
                labels[node.value] = found
        return labels
