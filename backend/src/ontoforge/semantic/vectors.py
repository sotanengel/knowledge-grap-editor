"""Local vector search, with no model and no network (§14 Phase 3).

The requirement that shaped this: OntoForge must work with the network unplugged
(NFR-06) and the image should stay under 400MB. A sentence-transformer would
break both. So the default here is **off**, and when it is switched on the
vectors come from hashed character n-grams computed in-process.

That is a weaker signal than a trained embedding -- it captures surface
similarity, not meaning -- and the tool says so rather than implying otherwise.
It is genuinely useful for the case it is good at: finding "田中太郎" from
"田中" or "たなか", and near-duplicate labels. Anything more needs a model, which
is an explicit opt-in the operator makes, not a default that quietly phones home.
"""

from __future__ import annotations

import math
import re
import sqlite3
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Self

INDEX_FILENAME = "vectors.sqlite3"
#: Hashing into a fixed number of buckets keeps every vector the same length
#: without needing a vocabulary.
DIMENSIONS = 512
#: Character n-gram sizes; 2 and 3 together handle CJK and latin alike.
NGRAM_SIZES = (2, 3)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vectors (
    iri TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    vector BLOB NOT NULL
);
"""

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class Similar:
    """One neighbour, with how close it is."""

    iri: str
    label: str
    score: float


def normalise(text: str) -> str:
    """Fold width and case so ＡＢＣ, ABC and abc hash alike."""
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", text).casefold()).strip()


def ngrams(text: str, sizes: Sequence[int] = NGRAM_SIZES) -> list[str]:
    cleaned = normalise(text)
    if not cleaned:
        return []
    found: list[str] = []
    for size in sizes:
        if len(cleaned) < size:
            found.append(cleaned)
            continue
        found.extend(cleaned[index : index + size] for index in range(len(cleaned) - size + 1))
    return found


def embed(text: str, *, dimensions: int = DIMENSIONS) -> list[float]:
    """A unit-length hashed n-gram vector. Deterministic, and offline."""
    vector = [0.0] * dimensions
    for gram in ngrams(text):
        # Python's hash() is salted per process, so a stable hash is needed for
        # an index that outlives the process.
        bucket = _stable_hash(gram) % dimensions
        vector[bucket] += 1.0

    length = math.sqrt(sum(value * value for value in vector))
    if length == 0.0:
        return vector
    return [value / length for value in vector]


def _stable_hash(text: str) -> int:
    import hashlib

    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "big")


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """Both vectors are unit length, so the dot product is the cosine."""
    return sum(a * b for a, b in zip(left, right, strict=True))


class VectorIndex:
    """The optional vector index, alongside the full-text one."""

    def __init__(self, directory: Path | str, *, dimensions: int = DIMENSIONS) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / INDEX_FILENAME
        self.dimensions = dimensions
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(_SCHEMA)
        self._connection.commit()

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
                (iri, label, _pack(embed(label, dimensions=self.dimensions))),
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
                [
                    (iri, label, _pack(embed(label, dimensions=self.dimensions)))
                    for iri, label in materialised
                ],
            )
        return len(materialised)

    # ------------------------------------------------------------------ reads

    def count(self) -> int:
        row = self._connection.execute("SELECT count(*) AS n FROM vectors").fetchone()
        return int(row["n"])

    def search(self, query: str, *, limit: int = 10, threshold: float = 0.0) -> list[Similar]:
        """Nearest labels first. A brute-force scan, which is fine at this scale."""
        target = embed(query, dimensions=self.dimensions)
        if not any(target):
            return []

        scored = [
            Similar(
                iri=row["iri"], label=row["label"], score=cosine(target, _unpack(row["vector"]))
            )
            for row in self._connection.execute("SELECT iri, label, vector FROM vectors")
        ]
        matching = [entry for entry in scored if entry.score > threshold]
        matching.sort(key=lambda entry: (-entry.score, entry.label))
        return matching[:limit]


def _pack(vector: Sequence[float]) -> bytes:
    import struct

    return struct.pack(f"<{len(vector)}f", *vector)


def _unpack(payload: bytes) -> list[float]:
    import struct

    return list(struct.unpack(f"<{len(payload) // 4}f", payload))
