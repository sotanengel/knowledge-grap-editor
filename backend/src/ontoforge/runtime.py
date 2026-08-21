"""The one long-lived object every service hangs off.

It owns the store, the change log, the snapshot policy and the search index, and
it is the only place that writes: every mutation goes through :meth:`Runtime.write`,
which records a patch, keeps the search index in step, snapshots when the policy
says so, and tells connected clients what happened.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import AsyncIterator, Iterable, Sequence
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any, Self

from pyoxigraph import NamedNode, Quad

from ontoforge.changelog.log import ACTOR_USER, ChangeLog
from ontoforge.changelog.patch import Patch
from ontoforge.changelog.snapshot import SnapshotPolicy, SnapshotStore
from ontoforge.config import Settings
from ontoforge.jsonld import Context, build_context, label_of
from ontoforge.namespaces import RDF_TYPE, RDFS_COMMENT
from ontoforge.search.fts import Kind, SearchIndex, SearchRecord
from ontoforge.store import graphs
from ontoforge.store.iri import IriMinter
from ontoforge.store.store import GraphStore

#: Graphs whose subjects are mirrored into the full-text index.
INDEXED_GRAPHS: tuple[NamedNode, ...] = (graphs.DATA, graphs.ONTOLOGY)

DEFAULT_SNAPSHOT_EVERY_OPS = 200
_EVENT_QUEUE_SIZE = 256


class EventBus:
    """Fan-out of change notifications to the ``GET /events`` SSE stream."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    def publish(self, event: dict[str, Any]) -> None:
        """Push an event to every listener, dropping it for any that fell behind."""
        for queue in list(self._subscribers):
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(event)

    @contextlib.asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_EVENT_QUEUE_SIZE)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


@dataclass(slots=True)
class Runtime:
    """Everything a request needs, assembled once at startup."""

    settings: Settings
    store: GraphStore
    changelog: ChangeLog
    snapshots: SnapshotStore
    search: SearchIndex
    minter: IriMinter
    policy: SnapshotPolicy
    events: EventBus = field(default_factory=EventBus)

    # ------------------------------------------------------------------ lifecycle

    @classmethod
    def create(cls, settings: Settings) -> Self:
        settings.ensure_directories()
        return cls(
            settings=settings,
            store=GraphStore.open(settings.store_dir),
            changelog=ChangeLog(settings.changelog_dir),
            snapshots=SnapshotStore(settings.snapshots_dir),
            search=SearchIndex(settings.index_dir),
            minter=IriMinter(settings.base_iri),
            policy=SnapshotPolicy(every_ops=DEFAULT_SNAPSHOT_EVERY_OPS),
        )

    def close(self) -> None:
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

    @property
    def context(self) -> Context:
        return build_context(self.settings.base_iri)

    # ------------------------------------------------------------------ writes

    def write(
        self,
        *,
        additions: Iterable[Quad] = (),
        deletions: Iterable[Quad] = (),
        actor: str = ACTOR_USER,
    ) -> Patch | None:
        """Apply a change, record it, reindex what it touched and announce it."""
        added = list(additions)
        deleted = list(deletions)
        patch = self.changelog.apply(self.store, additions=added, deletions=deleted, actor=actor)
        if patch is None:
            return None
        self._after_write(patch, "change")
        return patch

    def undo(self) -> Patch | None:
        patch = self.changelog.undo(self.store)
        if patch is not None:
            self._after_write(patch, "undo")
        return patch

    def redo(self) -> Patch | None:
        patch = self.changelog.redo(self.store)
        if patch is not None:
            self._after_write(patch, "redo")
        return patch

    def after_external_write(self, patch: Patch, *, kind: str = "change") -> None:
        """Bring the index, snapshots and listeners in step after a direct store write."""
        self._after_write(patch, kind)

    def _after_write(self, patch: Patch, kind: str) -> None:
        self.reindex_subjects(_touched_subjects(patch))
        if self.policy.should_snapshot(seq=patch.seq, now=time.monotonic()):
            self.snapshots.write(self.store, seq=patch.seq)
        self.events.publish(
            {
                "type": kind,
                "seq": patch.seq,
                "actor": patch.actor,
                "additions": len(patch.additions),
                "deletions": len(patch.deletions),
            }
        )

    # ------------------------------------------------------------------ index

    def reindex_subjects(self, subjects: Iterable[NamedNode]) -> None:
        """Recompute the search record of each subject, dropping the vanished ones."""
        for subject in subjects:
            record = self.search_record(subject)
            if record is None:
                self.search.delete(subject.value)
            else:
                self.search.upsert(record)

    def reindex_all(self) -> int:
        """Rebuild the whole index, e.g. after an import or a restore."""
        subjects = {
            quad.subject
            for graph in INDEXED_GRAPHS
            for quad in self.store.quads_for_pattern(None, None, None, graph)
            if isinstance(quad.subject, NamedNode)
        }
        records = [record for subject in subjects if (record := self.search_record(subject))]
        return self.search.replace_all(records)

    def search_record(self, subject: NamedNode) -> SearchRecord | None:
        """What the index should hold for ``subject``, or ``None`` if it is gone."""
        by_graph = {
            graph: list(self.store.quads_for_pattern(subject, None, None, graph))
            for graph in INDEXED_GRAPHS
        }
        quads = [quad for group in by_graph.values() for quad in group]
        if not quads:
            return None
        # A subject described in the ontology graph is a class or a property;
        # everything else is an instance. The canvas asks for one, the
        # vocabulary tree for the other.
        kind: Kind = "term" if by_graph[graphs.ONTOLOGY] else "instance"
        comments = [
            quad.object.value
            for quad in quads
            if quad.predicate == RDFS_COMMENT and hasattr(quad.object, "value")
        ]
        types = tuple(
            quad.object.value
            for quad in quads
            if quad.predicate == RDF_TYPE and isinstance(quad.object, NamedNode)
        )
        return SearchRecord(
            iri=subject.value,
            label=label_of(quads) or "",
            comment=" ".join(comments),
            types=types,
            kind=kind,
        )


def _touched_subjects(patch: Patch) -> set[NamedNode]:
    """Subjects (and referenced objects) whose index entry may have changed."""
    subjects: set[NamedNode] = set()
    for quad in (*patch.additions, *patch.deletions):
        if isinstance(quad.subject, NamedNode):
            subjects.add(quad.subject)
        if isinstance(quad.object, NamedNode):
            subjects.add(quad.object)
    return subjects


def quads_in(quads: Sequence[Quad], graph: NamedNode) -> list[Quad]:
    return [quad for quad in quads if quad.graph_name == graph]
