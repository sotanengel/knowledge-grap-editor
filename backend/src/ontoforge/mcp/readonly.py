"""The read-only view of the graph that MCP tools are allowed to see (§9).

This is where P4 is enforced, and it is enforced three times over:

1. **No update tool exists.** The surface in :mod:`ontoforge.mcp.server` is
   reference-only; there is nothing to call.
2. **The store refuses writes.** Over stdio -- a separate process -- that is
   pyoxigraph's own ``Store.read_only`` handle, exactly as §9 asks. The
   in-process HTTP mount shares the API's handle instead, because pyoxigraph
   documents a second handle on a live database as undefined behaviour; there
   the refusal is enforced by :meth:`GraphStore.read_only_view`, which raises on
   every mutating call. Either way nothing reaches the store.
3. **Query text is checked before it runs.** ``sparql_select`` accepts arbitrary
   SPARQL, so the text goes through the guard first.

The third layer exists because the first two cannot see inside a query string.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from pyoxigraph import NamedNode, Quad, Triple

from ontoforge.config import Settings
from ontoforge.io.graphview import local_name
from ontoforge.jsonld import label_of
from ontoforge.namespaces import (
    PROPERTY_TYPES,
    RDF_TYPE,
    RDFS_COMMENT,
    RDFS_DOMAIN,
    RDFS_RANGE,
    RDFS_SUBCLASS_OF,
)
from ontoforge.search.fts import SearchHit, SearchIndex
from ontoforge.sparql.guard import ensure_read_only
from ontoforge.store import graphs
from ontoforge.store.store import GraphStore

#: Nothing bigger comes back from one call, whatever was asked for (§9.5).
DEFAULT_LIMIT = 100
MAX_LIMIT = 500
DEFAULT_MAX_NODES = 100
DEFAULT_MAX_HOPS = 5


@dataclass(frozen=True, slots=True)
class Entity:
    """A node, always paired with its label so an IRI never travels alone (§9.5)."""

    iri: str
    label: str
    types: tuple[str, ...] = ()
    comment: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "iri": self.iri,
            "label": self.label,
            "types": list(self.types),
            "summary": self.comment,
        }


class ReadOnlyGraph:
    """A read-only handle on one ``/data`` directory."""

    def __init__(
        self,
        store: GraphStore,
        search: SearchIndex,
        settings: Settings,
        *,
        owns_resources: bool = True,
    ) -> None:
        if not store.read_only:
            raise ValueError("the MCP graph must be opened with a read-only store handle")
        self.store = store
        self.search = search
        self.settings = settings
        self._owns_resources = owns_resources

    @classmethod
    def open(cls, settings: Settings) -> Self:
        store_path = Path(settings.store_dir)
        if not store_path.is_dir():
            raise FileNotFoundError(
                f"no OntoForge store at {store_path}; start the server once to create it"
            )
        return cls(
            GraphStore.open_read_only(store_path),
            SearchIndex(settings.index_dir),
            settings,
        )

    @classmethod
    def sharing(cls, store: GraphStore, search: SearchIndex, settings: Settings) -> Self:
        """A read-only view over resources someone else owns (the in-process mount)."""
        return cls(store.read_only_view(), search, settings, owns_resources=False)

    def close(self) -> None:
        if not self._owns_resources:
            return
        self.search.close()
        self.store.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------ lookups

    def label_for(self, node: NamedNode) -> str:
        found = label_of(self.store.quads_for_pattern(node, None, None, None))
        return found if found is not None else local_name(node.value)

    def entity(self, node: NamedNode) -> Entity:
        quads = list(self.store.quads_for_pattern(node, None, None, None))
        comment = next(
            (
                quad.object.value
                for quad in quads
                if quad.predicate == RDFS_COMMENT and hasattr(quad.object, "value")
            ),
            "",
        )
        return Entity(
            iri=node.value,
            label=self.label_for(node),
            types=tuple(
                quad.object.value
                for quad in quads
                if quad.predicate == RDF_TYPE and isinstance(quad.object, NamedNode)
            ),
            comment=comment,
        )

    def find(
        self, query: str, *, type_iri: str | None = None, limit: int = DEFAULT_LIMIT
    ) -> list[Entity]:
        hits: Sequence[SearchHit] = self.search.search(
            query, type_iri=type_iri, limit=_clamp(limit)
        )
        return [
            Entity(iri=hit.iri, label=hit.label, types=hit.types, comment=hit.comment)
            for hit in hits
        ]

    def describe(self, node: NamedNode, *, depth: int = 1) -> list[Quad]:
        return self.store.describe(node, depth=max(1, min(depth, DEFAULT_MAX_HOPS)))

    def query(self, sparql: str) -> Any:
        """Run a query, but only after the guard has passed it."""
        ensure_read_only(sparql)
        return self.store.query(sparql)

    # ------------------------------------------------------------------ graph shape

    def classes(self) -> list[dict[str, Any]]:
        """Every class, with its parents and how many instances it has."""
        counts: dict[str, int] = {}
        for quad in self.store.quads_for_pattern(None, RDF_TYPE, None, graphs.DATA):
            if isinstance(quad.object, NamedNode):
                counts[quad.object.value] = counts.get(quad.object.value, 0) + 1

        found: dict[str, dict[str, Any]] = {}
        for graph in (graphs.ONTOLOGY, graphs.INFERRED):
            for quad in self.store.quads_for_pattern(None, RDF_TYPE, None, graph):
                if not isinstance(quad.subject, NamedNode) or quad.object in PROPERTY_TYPES:
                    continue
                iri = quad.subject.value
                found.setdefault(
                    iri,
                    {
                        "iri": iri,
                        "label": self.label_for(quad.subject),
                        "parents": [],
                        "instanceCount": counts.get(iri, 0),
                    },
                )
        for iri, entry in found.items():
            entry["parents"] = sorted(
                quad.object.value
                for quad in self.store.quads_for_pattern(
                    NamedNode(iri), RDFS_SUBCLASS_OF, None, graphs.ONTOLOGY
                )
                if isinstance(quad.object, NamedNode)
            )
        return sorted(found.values(), key=lambda entry: entry["label"])

    def properties(self, *, domain: str | None = None) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for quad in self.store.quads_for_pattern(None, RDF_TYPE, None, graphs.ONTOLOGY):
            if quad.object not in PROPERTY_TYPES or not isinstance(quad.subject, NamedNode):
                continue
            domains = _objects(self.store, quad.subject, RDFS_DOMAIN)
            if domain and domains and domain not in domains:
                continue
            found.append(
                {
                    "iri": quad.subject.value,
                    "label": self.label_for(quad.subject),
                    "domain": domains,
                    "range": _objects(self.store, quad.subject, RDFS_RANGE),
                }
            )
        return sorted(found, key=lambda entry: entry["label"])

    def neighbours(
        self, node: NamedNode, *, depth: int = 1, max_nodes: int = DEFAULT_MAX_NODES
    ) -> tuple[list[Entity], list[dict[str, str]]]:
        """The subgraph around ``node``, breadth first and capped."""
        seen: dict[str, NamedNode] = {node.value: node}
        edges: list[dict[str, str]] = []
        frontier = [node]

        for _ in range(max(1, min(depth, DEFAULT_MAX_HOPS))):
            following: list[NamedNode] = []
            for current in frontier:
                for quad in self._incident(current):
                    other = quad.object if quad.subject == current else quad.subject
                    if not isinstance(other, NamedNode):
                        continue
                    if not isinstance(quad.subject, NamedNode):
                        continue
                    edges.append(
                        {
                            "from": quad.subject.value,
                            "predicate": quad.predicate.value,
                            "predicateLabel": self.label_for(quad.predicate),
                            "to": other.value if quad.subject == current else current.value,
                        }
                    )
                    if other.value not in seen and len(seen) < max_nodes:
                        seen[other.value] = other
                        following.append(other)
            frontier = following
            if not frontier:
                break

        return [self.entity(found) for found in seen.values()], _unique(edges)

    def shortest_path(
        self, start: NamedNode, goal: NamedNode, *, max_hops: int = DEFAULT_MAX_HOPS
    ) -> list[dict[str, str]] | None:
        """Breadth-first shortest path, following edges in either direction."""
        if start == goal:
            return []
        visited = {start.value}
        frontier: list[tuple[NamedNode, list[dict[str, str]]]] = [(start, [])]

        for _ in range(max(1, max_hops)):
            following: list[tuple[NamedNode, list[dict[str, str]]]] = []
            for current, path in frontier:
                for quad in self._incident(current):
                    other = quad.object if quad.subject == current else quad.subject
                    if not isinstance(other, NamedNode) or other.value in visited:
                        continue
                    step = {
                        "from": current.value,
                        "fromLabel": self.label_for(current),
                        "predicate": quad.predicate.value,
                        "predicateLabel": self.label_for(quad.predicate),
                        "to": other.value,
                        "toLabel": self.label_for(other),
                        "direction": "out" if quad.subject == current else "in",
                    }
                    if other == goal:
                        return [*path, step]
                    visited.add(other.value)
                    following.append((other, [*path, step]))
            frontier = following
            if not frontier:
                break
        return None

    def _incident(self, node: NamedNode) -> list[Quad]:
        """Edges touching ``node``, ignoring type statements and literal attributes."""
        outgoing = [
            quad
            for quad in self.store.quads_for_pattern(node, None, None, None)
            if isinstance(quad.object, NamedNode) and quad.predicate != RDF_TYPE
        ]
        incoming = [
            quad
            for quad in self.store.quads_for_pattern(None, None, node, None)
            if isinstance(quad.subject, NamedNode) and quad.predicate != RDF_TYPE
        ]
        return [*outgoing, *incoming]

    # ------------------------------------------------------------------ stats

    def statistics(self) -> dict[str, Any]:
        return {
            "quads": self.store.count(),
            "instances": self.store.count(graphs.DATA),
            "ontology": self.store.count(graphs.ONTOLOGY),
            "inferred": self.store.count(graphs.INFERRED),
            "shapes": self.store.count(graphs.SHAPES),
            "vocabularies": sorted(
                graphs.vocab_name(graph)
                for graph in self.store.named_graphs()
                if graphs.is_vocab_graph(graph)
            ),
            "baseIri": self.settings.base_iri,
            "reasoner": self.settings.reasoner,
        }


def _objects(store: GraphStore, subject: NamedNode, predicate: NamedNode) -> list[str]:
    return sorted(
        quad.object.value
        for quad in store.quads_for_pattern(subject, predicate, None, graphs.ONTOLOGY)
        if isinstance(quad.object, NamedNode)
    )


def _unique(edges: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, str]] = []
    for edge in edges:
        key = (edge["from"], edge["predicate"], edge["to"])
        if key not in seen:
            seen.add(key)
            unique.append(edge)
    return unique


def _clamp(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def triple_of(quad: Quad | Triple) -> Triple:
    return quad if isinstance(quad, Triple) else Triple(quad.subject, quad.predicate, quad.object)
