"""The append-only change log (§5.2 C8, §6.4).

Every write to the graph goes through here, so the log is a complete account of
how the store reached its current state (NFR-08). Undo does **not** rewrite the
log: it appends the inverse patch. Replaying the file from the top therefore
always reproduces exactly what the user sees.

``actor`` records who made the change -- ``user``, ``import:<file>`` or
``reasoner``. Because MCP never writes, no entry can come from an AI (P4).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from pyoxigraph import Quad

from ontoforge.changelog.patch import Patch, parse_patches, serialize_patch
from ontoforge.store.store import GraphStore

LOG_FILENAME = "patches.rdfp"

ACTOR_USER = "user"
ACTOR_REASONER = "reasoner"


def import_actor(source: str) -> str:
    return f"import:{source}"


class ChangeLog:
    """The patch log living in one ``changelog/`` directory."""

    def __init__(self, directory: Path | str, *, filename: str = LOG_FILENAME) -> None:
        self.directory = Path(directory)
        self.path = self.directory / filename
        self._undo_stack: list[Patch] = []
        self._redo_stack: list[Patch] = []
        self._last_seq = 0
        self._reload()

    # ------------------------------------------------------------------ state

    def _reload(self) -> None:
        patches = self.read_all()
        self._last_seq = patches[-1].seq if patches else 0
        self._undo_stack = []
        self._redo_stack = []
        for patch in patches:
            self._track(patch)

    def _track(self, patch: Patch) -> None:
        """Fold one patch into the undo/redo stacks."""
        target = patch.inverse_of
        if target is not None and self._undo_stack and self._undo_stack[-1].id == target:
            self._undo_stack.pop()
            self._redo_stack.append(patch)
            return
        if target is not None and self._redo_stack and self._redo_stack[-1].id == target:
            self._redo_stack.pop()
            self._undo_stack.append(patch)
            return
        self._undo_stack.append(patch)
        self._redo_stack.clear()

    @property
    def last_seq(self) -> int:
        return self._last_seq

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    # ------------------------------------------------------------------ read

    def read_all(self) -> list[Patch]:
        if not self.path.is_file():
            return []
        return parse_patches(self.path.read_text(encoding="utf-8"))

    def __iter__(self) -> Iterator[Patch]:
        return iter(self.read_all())

    def history(self, *, limit: int | None = None) -> list[Patch]:
        """Recorded changes, newest first."""
        patches = list(reversed(self.read_all()))
        return patches if limit is None else patches[:limit]

    def patches_after(self, seq: int, *, upto: int | None = None) -> list[Patch]:
        return [
            patch
            for patch in self.read_all()
            if patch.seq > seq and (upto is None or patch.seq <= upto)
        ]

    # ------------------------------------------------------------------ write

    def apply(
        self,
        store: GraphStore,
        *,
        additions: Iterable[Quad] = (),
        deletions: Iterable[Quad] = (),
        actor: str = ACTOR_USER,
    ) -> Patch | None:
        """Write a change to the store and record it. ``None`` if nothing changed."""
        patch = Patch.create(
            seq=self._last_seq + 1,
            actor=actor,
            additions=additions,
            deletions=deletions,
        )
        if patch.is_empty:
            return None
        return self._commit(store, patch)

    def record(
        self,
        *,
        additions: Iterable[Quad] = (),
        deletions: Iterable[Quad] = (),
        actor: str = ACTOR_USER,
    ) -> Patch | None:
        """Record a change that has *already* reached the store.

        SPARQL Update writes straight through pyoxigraph, so the caller works
        out what changed by diffing and hands the result here.
        """
        patch = Patch.create(
            seq=self._last_seq + 1,
            actor=actor,
            additions=additions,
            deletions=deletions,
        )
        if patch.is_empty:
            return None
        return self._commit(None, patch)

    def undo(self, store: GraphStore) -> Patch | None:
        """Undo the most recent change by appending its inverse."""
        if not self._undo_stack:
            return None
        return self._commit(store, self._undo_stack[-1].invert(seq=self._last_seq + 1))

    def redo(self, store: GraphStore) -> Patch | None:
        """Redo the most recently undone change, again by appending."""
        if not self._redo_stack:
            return None
        return self._commit(store, self._redo_stack[-1].invert(seq=self._last_seq + 1))

    def _commit(self, store: GraphStore | None, patch: Patch) -> Patch:
        if store is not None:
            apply_patch(store, patch)
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(serialize_patch(patch))
        self._last_seq = patch.seq
        self._track(patch)
        return patch


def apply_patch(store: GraphStore, patch: Patch) -> None:
    """Apply one patch to ``store``: deletions first, then additions."""
    if patch.deletions:
        store.remove(patch.deletions)
    if patch.additions:
        store.add(patch.additions)
