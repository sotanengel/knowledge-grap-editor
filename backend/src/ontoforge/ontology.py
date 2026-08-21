"""Class and property definitions -- the TBox (§8, FR-03).

Ontology terms differ from instances in one important way: their IRIs are
readable, derived from the label, because those are the names a person reads in
exported Turtle. That makes them renameable, and a rename has to rewrite every
reference in one go (§6.2).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any
from typing import Literal as LiteralType

from pyoxigraph import NamedNode, Quad

from ontoforge.entities import DEFAULT_LANGUAGE
from ontoforge.jsonld import build_context, expand_iri, label_of, node_document, with_context
from ontoforge.literals import make_literal
from ontoforge.namespaces import (
    OWL_CLASS,
    OWL_DATATYPE_PROPERTY,
    OWL_OBJECT_PROPERTY,
    PROPERTY_TYPES,
    RDF_TYPE,
    RDFS_COMMENT,
    RDFS_DOMAIN,
    RDFS_LABEL,
    RDFS_RANGE,
    RDFS_SUBCLASS_OF,
    RDFS_SUBPROPERTY_OF,
)
from ontoforge.runtime import Runtime
from ontoforge.store import graphs

PropertyKind = LiteralType["object", "datatype"]

_PROPERTY_TYPE_OF: dict[str, NamedNode] = {
    "object": OWL_OBJECT_PROPERTY,
    "datatype": OWL_DATATYPE_PROPERTY,
}


class TermNotFoundError(LookupError):
    """Raised when an ontology term IRI names nothing."""


class OntologyService:
    """Read and edit ``urn:ontoforge:ontology``."""

    def __init__(self, runtime: Runtime, *, graph: NamedNode = graphs.ONTOLOGY) -> None:
        self.runtime = runtime
        self.graph = graph
        self.context = build_context(runtime.settings.base_iri)

    # ------------------------------------------------------------------ write

    def add_class(
        self,
        *,
        label: str,
        parents: Iterable[str] = (),
        comment: str | None = None,
        language: str = DEFAULT_LANGUAGE,
        actor: str = "user",
    ) -> dict[str, Any]:
        """Define a class. A label already in use returns the existing term."""
        cleaned = self._require_label(label)
        subject = self.runtime.minter.class_iri(cleaned)
        quads = self._definition_quads(
            subject, OWL_CLASS, cleaned, comment, language, RDFS_SUBCLASS_OF, parents
        )
        self._write_new(subject, quads, actor)
        return self.get(subject.value)

    def add_property(
        self,
        *,
        label: str,
        kind: PropertyKind = "object",
        parents: Iterable[str] = (),
        domain: str | None = None,
        range_: str | None = None,
        comment: str | None = None,
        language: str = DEFAULT_LANGUAGE,
        actor: str = "user",
    ) -> dict[str, Any]:
        """Define a property, optionally constraining its domain and range."""
        if kind not in _PROPERTY_TYPE_OF:
            raise ValueError(f"unknown property kind {kind!r}")
        cleaned = self._require_label(label)
        subject = self.runtime.minter.property_iri(cleaned)
        quads = self._definition_quads(
            subject,
            _PROPERTY_TYPE_OF[kind],
            cleaned,
            comment,
            language,
            RDFS_SUBPROPERTY_OF,
            parents,
        )
        for predicate, value in ((RDFS_DOMAIN, domain), (RDFS_RANGE, range_)):
            if value:
                quads.append(Quad(subject, predicate, self._node(value), self.graph))
        self._write_new(subject, quads, actor)
        return self.get(subject.value)

    def rename(self, iri: str, new_label: str, *, actor: str = "user") -> dict[str, Any]:
        """Give a term a new IRI, rewriting every reference to it (§6.2)."""
        old = self._node(iri)
        existing = list(self.runtime.store.quads_for_pattern(old, None, None, self.graph))
        if not existing:
            raise TermNotFoundError(iri)

        cleaned = self._require_label(new_label)
        is_property = any(
            quad.predicate == RDF_TYPE and quad.object in PROPERTY_TYPES for quad in existing
        )
        new = (
            self.runtime.minter.property_iri(cleaned)
            if is_property
            else self.runtime.minter.class_iri(cleaned)
        )

        references = [
            quad
            for quad in self.runtime.store.quads_for_pattern(None, None, old, None)
            if quad.subject != old
        ]
        deletions = [*existing, *references]
        additions = [
            Quad(new, quad.predicate, quad.object, quad.graph_name)
            for quad in existing
            if quad.predicate != RDFS_LABEL
        ]
        additions.append(
            Quad(new, RDFS_LABEL, make_literal(cleaned, language=DEFAULT_LANGUAGE), self.graph)
        )
        additions.extend(
            Quad(quad.subject, quad.predicate, new, quad.graph_name) for quad in references
        )

        self.runtime.write(additions=additions, deletions=deletions, actor=actor)
        return self.get(new.value)

    # ------------------------------------------------------------------ read

    def get(self, iri: str) -> dict[str, Any]:
        node = self._node(iri)
        quads = list(self.runtime.store.quads_for_pattern(node, None, None, self.graph))
        if not quads:
            raise TermNotFoundError(iri)
        return with_context(node_document(node.value, quads), self.context)

    def tree(self) -> dict[str, Any]:
        """The class hierarchy and the property list, ready for the left pane (§7.1)."""
        classes = self._terms(is_property=False)
        properties = self._terms(is_property=True)
        return {
            "classes": _nest(classes, parent_key="parents"),
            "properties": sorted(properties.values(), key=lambda term: term["label"]),
        }

    def candidate_properties(self, *, domain: str | None = None) -> list[dict[str, Any]]:
        """Properties offered when drawing an edge out of a node of ``domain`` (§7.2).

        A property with no declared domain fits anywhere, so it is always offered.
        """
        expanded = self._expand(domain) if domain else None
        properties = self._terms(is_property=True).values()
        if expanded is None:
            return sorted(properties, key=lambda term: term["label"])
        matching = [term for term in properties if not term["domain"] or expanded in term["domain"]]
        return sorted(matching, key=lambda term: term["label"])

    def instance_counts(self) -> dict[str, int]:
        """How many instances each class has, for the tree and for ``describe_ontology``."""
        counts: dict[str, int] = {}
        for quad in self.runtime.store.quads_for_pattern(None, RDF_TYPE, None, graphs.DATA):
            if isinstance(quad.object, NamedNode):
                counts[quad.object.value] = counts.get(quad.object.value, 0) + 1
        return counts

    # ------------------------------------------------------------------ helpers

    def _terms(self, *, is_property: bool) -> dict[str, dict[str, Any]]:
        parent_predicate = RDFS_SUBPROPERTY_OF if is_property else RDFS_SUBCLASS_OF
        counts = self.instance_counts()
        by_subject: dict[NamedNode, list[Quad]] = {}
        for quad in self.runtime.store.quads_for_pattern(None, None, None, self.graph):
            if isinstance(quad.subject, NamedNode):
                by_subject.setdefault(quad.subject, []).append(quad)

        terms: dict[str, dict[str, Any]] = {}
        for subject, quads in by_subject.items():
            types = {quad.object for quad in quads if quad.predicate == RDF_TYPE}
            if is_property != bool(types & set(PROPERTY_TYPES)):
                continue
            terms[subject.value] = {
                "iri": subject.value,
                "label": label_of(quads) or subject.value.rsplit("#", 1)[-1],
                "comment": _first(quads, RDFS_COMMENT),
                "types": sorted(term.value for term in types if isinstance(term, NamedNode)),
                "parents": _objects(quads, parent_predicate),
                "domain": _objects(quads, RDFS_DOMAIN),
                "range": _objects(quads, RDFS_RANGE),
                "instanceCount": counts.get(subject.value, 0),
                "children": [],
            }
        return terms

    def _definition_quads(
        self,
        subject: NamedNode,
        type_node: NamedNode,
        label: str,
        comment: str | None,
        language: str,
        parent_predicate: NamedNode,
        parents: Iterable[str],
    ) -> list[Quad]:
        quads = [
            Quad(subject, RDF_TYPE, type_node, self.graph),
            Quad(subject, RDFS_LABEL, make_literal(label, language=language), self.graph),
        ]
        if comment:
            quads.append(
                Quad(subject, RDFS_COMMENT, make_literal(comment, language=language), self.graph)
            )
        quads.extend(
            Quad(subject, parent_predicate, self._node(parent), self.graph) for parent in parents
        )
        return quads

    def _write_new(self, subject: NamedNode, quads: Sequence[Quad], actor: str) -> None:
        """Assert only what is not already there, so a re-definition is idempotent."""
        fresh = [quad for quad in quads if not self.runtime.store.contains(quad)]
        if fresh:
            self.runtime.write(additions=fresh, actor=actor)

    def _require_label(self, label: str) -> str:
        cleaned = label.strip()
        if not cleaned:
            raise ValueError("label must not be empty")
        return cleaned

    def _expand(self, term: str) -> str:
        return expand_iri(term, self.context)

    def _node(self, term: str) -> NamedNode:
        return NamedNode(self._expand(term))


def _objects(quads: Iterable[Quad], predicate: NamedNode) -> list[str]:
    return sorted(
        quad.object.value
        for quad in quads
        if quad.predicate == predicate and isinstance(quad.object, NamedNode)
    )


def _first(quads: Iterable[Quad], predicate: NamedNode) -> str | None:
    for quad in quads:
        if quad.predicate == predicate and hasattr(quad.object, "value"):
            return str(quad.object.value)
    return None


def _nest(terms: dict[str, dict[str, Any]], *, parent_key: str) -> list[dict[str, Any]]:
    """Turn a flat term map into a forest, tolerating cycles and missing parents."""
    roots: list[dict[str, Any]] = []
    for iri, term in terms.items():
        parents = [parent for parent in term[parent_key] if parent in terms and parent != iri]
        if parents:
            for parent in parents:
                terms[parent]["children"].append(term)
        else:
            roots.append(term)

    if not roots and terms:
        # Every term sits in a cycle; surface them all rather than nothing.
        roots = list(terms.values())
    return sorted(roots, key=lambda term: term["label"])
