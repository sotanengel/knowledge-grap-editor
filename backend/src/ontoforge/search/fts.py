"""SQLite FTS5 label index (§5.2 C6, FR-08).

Oxigraph has no full-text index, so labels and comments are mirrored into a
small SQLite database. SQLite ships with Python, so this costs no extra
dependency and nothing extra in the container.

The table uses the ``trigram`` tokenizer, which is what makes Japanese work:
there are no word boundaries to tokenise on, and trigrams also let SQLite use
the index for ``LIKE '%...%'``. Queries of three characters or more go through
``MATCH`` so they come back ranked; shorter ones -- "田中" is two characters --
fall back to the index-accelerated ``LIKE``.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Self

INDEX_FILENAME = "search.sqlite3"
#: ASCII unit separator: cannot occur inside an IRI, so joining types is safe.
TYPE_SEPARATOR = "\x1f"
_MIN_TRIGRAM_LENGTH = 3

_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS entities USING fts5(
    iri UNINDEXED,
    label,
    comment,
    types UNINDEXED,
    tokenize='trigram'
);
"""


@dataclass(frozen=True, slots=True)
class SearchRecord:
    """What the index knows about one node."""

    iri: str
    label: str
    comment: str = ""
    types: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One result row."""

    iri: str
    label: str
    comment: str
    types: tuple[str, ...]


class SearchIndex:
    """The ``index/`` directory."""

    def __init__(self, directory: Path | str, *, filename: str = INDEX_FILENAME) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / filename
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(_SCHEMA)
        self._connection.commit()

    # ------------------------------------------------------------------ lifecycle

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

    def upsert(self, record: SearchRecord) -> None:
        """Insert or replace one record. FTS5 has no UPSERT, so delete then insert."""
        with self._connection:
            self._delete(record.iri)
            self._insert(record)

    def upsert_many(self, records: Iterable[SearchRecord]) -> int:
        materialised = list(records)
        with self._connection:
            for record in materialised:
                self._delete(record.iri)
                self._insert(record)
        return len(materialised)

    def delete(self, iri: str) -> None:
        with self._connection:
            self._delete(iri)

    def clear(self) -> None:
        with self._connection:
            self._connection.execute("DELETE FROM entities")

    def replace_all(self, records: Iterable[SearchRecord]) -> int:
        """Rebuild the whole index, e.g. after an import or a restore."""
        materialised = list(records)
        with self._connection:
            self._connection.execute("DELETE FROM entities")
            for record in materialised:
                self._insert(record)
        return len(materialised)

    def _insert(self, record: SearchRecord) -> None:
        self._connection.execute(
            "INSERT INTO entities (iri, label, comment, types) VALUES (?, ?, ?, ?)",
            (record.iri, record.label, record.comment, TYPE_SEPARATOR.join(record.types)),
        )

    def _delete(self, iri: str) -> None:
        self._connection.execute("DELETE FROM entities WHERE iri = ?", (iri,))

    # ------------------------------------------------------------------ reads

    def count(self) -> int:
        row = self._connection.execute("SELECT count(*) AS n FROM entities").fetchone()
        return int(row["n"])

    def search(
        self,
        query: str,
        *,
        type_iri: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SearchHit]:
        """Find nodes whose label or comment matches ``query``."""
        if limit < 0 or offset < 0:
            raise ValueError("limit and offset must not be negative")

        term = query.strip()
        conditions: list[str] = []
        parameters: list[object] = []
        order = "rowid"

        if len(term) >= _MIN_TRIGRAM_LENGTH:
            conditions.append("entities MATCH ?")
            parameters.append(_quote_for_fts(term))
            order = "rank"
        elif term:
            conditions.append("(label LIKE ? OR comment LIKE ?)")
            pattern = f"%{_escape_like(term)}%"
            parameters.extend([pattern, pattern])

        if type_iri:
            conditions.append("(types = ? OR types LIKE ? OR types LIKE ? OR types LIKE ?)")
            parameters.extend(
                [
                    type_iri,
                    f"{type_iri}{TYPE_SEPARATOR}%",
                    f"%{TYPE_SEPARATOR}{type_iri}",
                    f"%{TYPE_SEPARATOR}{type_iri}{TYPE_SEPARATOR}%",
                ]
            )

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = (
            "SELECT iri, label, comment, types FROM entities"
            f"{where} ORDER BY {order} LIMIT ? OFFSET ?"
        )
        parameters.extend([limit, offset])

        try:
            rows = self._connection.execute(sql, parameters).fetchall()
        except sqlite3.OperationalError:
            # A query FTS5 cannot parse means "no matches", never a 500.
            return []
        return [_hit(row) for row in rows]

    def all_records(self) -> list[SearchHit]:
        rows = self._connection.execute(
            "SELECT iri, label, comment, types FROM entities ORDER BY rowid"
        ).fetchall()
        return [_hit(row) for row in rows]


def _hit(row: sqlite3.Row) -> SearchHit:
    raw_types: str = row["types"]
    return SearchHit(
        iri=row["iri"],
        label=row["label"],
        comment=row["comment"],
        types=tuple(part for part in raw_types.split(TYPE_SEPARATOR) if part),
    )


def _quote_for_fts(term: str) -> str:
    """Wrap the query as a single FTS5 string so its punctuation stays literal."""
    return '"' + term.replace('"', '""') + '"'


def _escape_like(term: str) -> str:
    return term.replace("%", r"\%").replace("_", r"\_")
