"""The vector index behind similar-label search (§14 Phase 3).

A small SQLite table of one vector per label, scanned in full at query time.
That is fine at the scale this tool targets (§15.2 Q2: tens of thousands of
triples) and avoids a vector-database dependency for a feature that is off by
default.

What produced the vectors matters more than how they are stored: an index built
by one embedder cannot be searched with another, because the numbers mean
different things. The embedder is recorded alongside the vectors and a mismatch
empties the index rather than returning quiet nonsense -- the same reasoning as
the full-text index's schema version.
"""

from __future__ import annotations

import sqlite3
import struct
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Self

from ontoforge.semantic.embedder import Embedder, cosine, load_embedder

INDEX_FILENAME = "vectors.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vectors (
    iri TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    vector BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    embedder TEXT NOT NULL,
    dimensions INTEGER NOT NULL
);
"""


@dataclass(frozen=True, slots=True)
class Similar:
    """One neighbour, with how close it is."""

    iri: str
    label: str
    score: float


class VectorIndex:
    """The optional vector index, alongside the full-text one."""

    def __init__(
        self,
        directory: Path | str,
        *,
        embedder: Embedder | None = None,
    ) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / INDEX_FILENAME
        self.embedder = embedder if embedder is not None else load_embedder()

        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._prepare()

    @property
    def dimensions(self) -> int:
        return self.embedder.dimensions

    # ------------------------------------------------------------------ lifecycle

    def _prepare(self) -> None:
        """Create the table, emptying it if a different embedder filled it."""
        self._connection.executescript(_SCHEMA)
        row = self._connection.execute("SELECT embedder, dimensions FROM meta").fetchone()

        matches = (
            row is not None
            and row["embedder"] == self.embedder.name
            and int(row["dimensions"]) == self.embedder.dimensions
        )
        if not matches:
            # Vectors from two embedders are not comparable, so the old ones go.
            # The index is a derived cache; the runtime refills it.
            self._connection.execute("DELETE FROM vectors")
            self._connection.execute("DELETE FROM meta")
            self._connection.execute(
                "INSERT INTO meta (embedder, dimensions) VALUES (?, ?)",
                (self.embedder.name, self.embedder.dimensions),
            )
        self._connection.commit()

    @property
    def stale(self) -> bool:
        """Whether the index is empty and needs repopulating."""
        return self.count() == 0

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------ writes

    def upsert(self, iri: str, label: str) -> None:
        with self._connection:
            self._connection.execute(
                "INSERT INTO vectors (iri, label, vector) VALUES (?, ?, ?) "
                "ON CONFLICT(iri) DO UPDATE SET label = excluded.label, vector = excluded.vector",
                (iri, label, _pack(self.embedder.embed(label))),
            )

    def delete(self, iri: str) -> None:
        with self._connection:
            self._connection.execute("DELETE FROM vectors WHERE iri = ?", (iri,))

    def replace_all(self, entries: Iterable[tuple[str, str]]) -> int:
        materialised = list(entries)
        with self._connection:
            self._connection.execute("DELETE FROM vectors")
            self._connection.executemany(
                "INSERT INTO vectors (iri, label, vector) VALUES (?, ?, ?)",
                [(iri, label, _pack(self.embedder.embed(label))) for iri, label in materialised],
            )
        return len(materialised)

    def clear(self) -> None:
        with self._connection:
            self._connection.execute("DELETE FROM vectors")

    # ------------------------------------------------------------------ reads

    def count(self) -> int:
        row = self._connection.execute("SELECT count(*) AS n FROM vectors").fetchone()
        return int(row["n"])

    def search(self, query: str, *, limit: int = 10, threshold: float = 0.0) -> list[Similar]:
        """Nearest labels first. A full scan, which is fine at this scale."""
        target = self.embedder.embed(query)
        if not any(target):
            return []

        scored = [
            Similar(
                iri=row["iri"],
                label=row["label"],
                score=cosine(target, _unpack(row["vector"])),
            )
            for row in self._connection.execute("SELECT iri, label, vector FROM vectors")
        ]
        matching = [entry for entry in scored if entry.score > threshold]
        matching.sort(key=lambda entry: (-entry.score, entry.label))
        return matching[:limit]


def _pack(vector: list[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def _unpack(payload: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(payload) // 4}f", payload))
