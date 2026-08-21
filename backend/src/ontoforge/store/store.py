"""The RDF store (§5.2 C3).

pyoxigraph is embedded in the API process rather than run as a separate
database, which is what lets the whole product ship as one container (P2).

The wrapper exists mostly for one reason: it can be opened **read-only**, and
a read-only handle refuses every mutating call. That is the second of the three
defences that keep the MCP server from writing to the graph (§9, §13).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from pyoxigraph import (
    BlankNode,
    DefaultGraph,
    NamedNode,
    Quad,
    QuerySolutions,
    RdfFormat,
    Store,
    Triple,
    parse,
)

from ontoforge.store import graphs
from ontoforge.store.iri import SKOLEM_SUFFIX

GraphName = NamedNode | DefaultGraph
Subject = NamedNode | BlankNode | Triple
Term = NamedNode | BlankNode | Triple | Any


class ReadOnlyStoreError(RuntimeError):
    """Raised when a mutating call reaches a store opened read-only."""


class StoreClosedError(RuntimeError):
    """Raised when a closed store is used again."""


class GraphStore:
    """A quad store scoped to one ``/data/store`` directory."""

    def __init__(
        self, store: Store, *, path: Path, read_only: bool, owns_handle: bool = True
    ) -> None:
        self._store: Store | None = store
        self._path = path
        self._read_only = read_only
        self._owns_handle = owns_handle

    # ------------------------------------------------------------------ open

    @classmethod
    def open(cls, path: Path | str) -> Self:
        """Open (creating if needed) a read-write store at ``path``."""
        resolved = Path(path)
        resolved.mkdir(parents=True, exist_ok=True)
        return cls(Store(str(resolved)), path=resolved, read_only=False)

    @classmethod
    def open_read_only(cls, path: Path | str) -> Self:
        """Open an existing store read-only.

        The restriction is enforced by pyoxigraph itself, not by a flag this
        process could forget to check.
        """
        resolved = Path(path)
        if not resolved.is_dir():
            raise FileNotFoundError(f"no RDF store at {resolved}")
        return cls(Store.read_only(str(resolved)), path=resolved, read_only=True)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def read_only(self) -> bool:
        return self._read_only

    def read_only_view(self) -> GraphStore:
        """A read-only wrapper over the *same* handle.

        Two pyoxigraph handles on one live database are not safe -- ``Store.read_only``
        is documented as undefined behaviour while another writer is open -- so a
        component that must not write while sharing this process gets this instead:
        the same handle, with every mutating method refused at the wrapper.

        A genuinely separate read-only handle is what :meth:`open_read_only` is
        for, and it is what the out-of-process MCP transport uses.
        """
        return GraphStore(self._raw, path=self._path, read_only=True, owns_handle=False)

    def close(self) -> None:
        """Release the store, and with it the on-disk lock."""
        store = self._store
        self._store = None
        if store is None or not self._owns_handle:
            return
        if not self._read_only:
            store.flush()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------ guards

    @property
    def _raw(self) -> Store:
        if self._store is None:
            raise StoreClosedError(f"store at {self._path} is closed")
        return self._store

    def _writable(self) -> Store:
        if self._read_only:
            raise ReadOnlyStoreError(f"store at {self._path} is open read-only")
        return self._raw

    # ------------------------------------------------------------------ writes

    def add(self, quads: Iterable[Quad]) -> int:
        """Insert ``quads``; returns how many were handed to the store."""
        store = self._writable()
        materialised = list(quads)
        store.extend(materialised)
        return len(materialised)

    def remove(self, quads: Iterable[Quad]) -> int:
        store = self._writable()
        removed = 0
        for quad in quads:
            store.remove(quad)
            removed += 1
        return removed

    def clear_graph(self, graph: GraphName) -> None:
        self._writable().clear_graph(graph)

    def clear(self) -> None:
        self._writable().clear()

    def update(self, update: str) -> None:
        """Run a SPARQL Update. Never reachable through a read-only handle."""
        self._writable().update(update)

    # ------------------------------------------------------------------ reads

    def query(self, query: str, **kwargs: Any) -> Any:
        return self._raw.query(query, **kwargs)

    def select(self, query: str, **kwargs: Any) -> QuerySolutions:
        result = self._raw.query(query, **kwargs)
        if not isinstance(result, QuerySolutions):
            raise TypeError("query did not return a solution sequence")
        return result

    def quads_for_pattern(
        self,
        subject: Subject | None = None,
        predicate: NamedNode | None = None,
        obj: Term | None = None,
        graph: GraphName | None = None,
    ) -> Iterator[Quad]:
        return iter(self._raw.quads_for_pattern(subject, predicate, obj, graph))

    def count(self, graph: GraphName | None = None) -> int:
        return sum(1 for _ in self._raw.quads_for_pattern(None, None, None, graph))

    def named_graphs(self) -> list[NamedNode]:
        return [g for g in self._raw.named_graphs() if isinstance(g, NamedNode)]

    def contains(self, quad: Quad) -> bool:
        return quad in self._raw

    # ------------------------------------------------------------------ CBD

    def describe(
        self,
        node: Subject,
        *,
        depth: int = 1,
        search: Sequence[GraphName] | None = None,
    ) -> list[Quad]:
        """Concise Bounded Description of ``node``.

        ``depth`` of 1 is the CBD proper: every quad with ``node`` as subject,
        plus, recursively, the description of any blank node it reaches.
        Higher values follow named objects too, which is what ``?depth=`` on
        ``GET /entities/{iri}`` exposes.
        """
        if depth < 1:
            raise ValueError("depth must be at least 1")
        candidates = (
            list(search)
            if search is not None
            else [g for g in self.named_graphs() if g != graphs.LAYOUT]
        )

        collected: list[Quad] = []
        seen_quads: set[Quad] = set()
        visited: set[Subject] = set()
        frontier: list[tuple[Subject, int]] = [(node, depth)]

        while frontier:
            current, remaining = frontier.pop()
            if current in visited:
                continue
            visited.add(current)
            for graph in candidates:
                for quad in self._raw.quads_for_pattern(current, None, None, graph):
                    if quad in seen_quads:
                        continue
                    seen_quads.add(quad)
                    collected.append(quad)
                    obj = quad.object
                    # Blank nodes are always part of the description; named
                    # nodes only while budget remains.
                    if isinstance(obj, BlankNode):
                        frontier.append((obj, remaining))
                    elif isinstance(obj, NamedNode) and remaining > 1:
                        frontier.append((obj, remaining - 1))
        return collected

    # ------------------------------------------------------------------ io

    def dump_graph(
        self,
        graph: GraphName,
        *,
        rdf_format: RdfFormat = RdfFormat.TURTLE,
        prefixes: dict[str, str] | None = None,
    ) -> str:
        payload = self._raw.dump(format=rdf_format, from_graph=graph, prefixes=prefixes)
        return payload.decode("utf-8") if isinstance(payload, bytes) else str(payload)

    def dump_dataset(
        self,
        *,
        rdf_format: RdfFormat = RdfFormat.TRIG,
        prefixes: dict[str, str] | None = None,
    ) -> str:
        payload = self._raw.dump(format=rdf_format, prefixes=prefixes)
        return payload.decode("utf-8") if isinstance(payload, bytes) else str(payload)

    def load_graph(
        self,
        payload: str | bytes,
        graph: GraphName,
        *,
        rdf_format: RdfFormat = RdfFormat.TURTLE,
        base_iri: str | None = None,
        skolemize_base: str | None = None,
    ) -> int:
        """Load ``payload`` into a single graph, optionally skolemising blank nodes."""
        quads = [
            Quad(item.subject, item.predicate, item.object, graph)
            for item in parse(payload, format=rdf_format, base_iri=base_iri)
        ]
        if skolemize_base is not None:
            quads = [skolemize_quad(quad, skolemize_base) for quad in quads]
        return self.add(quads)

    def load_dataset(
        self,
        payload: str | bytes,
        *,
        rdf_format: RdfFormat = RdfFormat.TRIG,
        base_iri: str | None = None,
        skolemize_base: str | None = None,
    ) -> int:
        """Load a quad payload, keeping the graph names it carries."""
        quads = [
            item if isinstance(item, Quad) else Quad(item.subject, item.predicate, item.object)
            for item in parse(payload, format=rdf_format, base_iri=base_iri)
        ]
        if skolemize_base is not None:
            quads = [skolemize_quad(quad, skolemize_base) for quad in quads]
        return self.add(quads)


def skolemize_term(term: Any, base_iri: str) -> Any:
    """Replace blank nodes with `.well-known/genid` IRIs, recursing into quoted triples."""
    if isinstance(term, BlankNode):
        separator = "" if base_iri.endswith(("/", "#")) else "/"
        return NamedNode(f"{base_iri}{separator}{SKOLEM_SUFFIX}{term.value}")
    if isinstance(term, Triple):
        return Triple(
            skolemize_term(term.subject, base_iri),
            term.predicate,
            skolemize_term(term.object, base_iri),
        )
    return term


def skolemize_quad(quad: Quad, base_iri: str) -> Quad:
    return Quad(
        skolemize_term(quad.subject, base_iri),
        quad.predicate,
        skolemize_term(quad.object, base_iri),
        quad.graph_name,
    )
