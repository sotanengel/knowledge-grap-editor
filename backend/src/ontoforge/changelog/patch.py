"""RDF Patch serialisation (§6.4).

One user operation is one patch, and one patch is one undo step. The format is
the ``A`` / ``D`` line dialect of RDF Patch with a small header block, chosen
because it diffs well in Git and reads plainly.

    H id     "01J8Z3K5..." .
    H seq    "7" .
    H time   "2026-08-21T09:00:00+00:00" .
    H actor  "user" .
    TX .
    A <s> <p> <o> <g> .
    D <s> <p> <o> .
    TC .
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from pyoxigraph import DefaultGraph, Quad, RdfFormat, parse
from ulid import ULID

TX_BEGIN = "TX ."
TX_COMMIT = "TC ."
_HEADER = "H "

_ESCAPES = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}
_UNESCAPES = {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t"}


class PatchParseError(ValueError):
    """Raised when a changelog stream is not well formed."""


def _escape(value: str) -> str:
    return "".join(_ESCAPES.get(character, character) for character in value)


def _unescape(value: str) -> str:
    result: list[str] = []
    iterator = iter(value)
    for character in iterator:
        if character != "\\":
            result.append(character)
            continue
        try:
            following = next(iterator)
        except StopIteration as error:
            raise PatchParseError(f"dangling escape in {value!r}") from error
        result.append(_UNESCAPES.get(following, following))
    return "".join(result)


@dataclass(frozen=True, slots=True)
class Patch:
    """One atomic change to the graph."""

    id: str
    seq: int
    timestamp: datetime
    actor: str
    additions: tuple[Quad, ...] = ()
    deletions: tuple[Quad, ...] = ()
    inverse_of: str | None = field(default=None)

    @classmethod
    def create(
        cls,
        *,
        seq: int,
        actor: str,
        additions: Iterable[Quad] = (),
        deletions: Iterable[Quad] = (),
        inverse_of: str | None = None,
        timestamp: datetime | None = None,
    ) -> Patch:
        if seq < 1:
            raise ValueError("seq must be at least 1")
        if not actor:
            raise ValueError("actor must not be empty")
        return cls(
            id=str(ULID()),
            seq=seq,
            timestamp=timestamp or datetime.now(UTC),
            actor=actor,
            additions=tuple(additions),
            deletions=tuple(deletions),
            inverse_of=inverse_of,
        )

    @property
    def is_empty(self) -> bool:
        return not self.additions and not self.deletions

    @property
    def size(self) -> int:
        return len(self.additions) + len(self.deletions)

    def invert(self, *, seq: int, actor: str | None = None) -> Patch:
        """The patch that undoes this one."""
        return Patch.create(
            seq=seq,
            actor=actor or self.actor,
            additions=self.deletions,
            deletions=self.additions,
            inverse_of=self.id,
        )


def serialize_patch(patch: Patch) -> str:
    lines = [
        f'{_HEADER}id "{_escape(patch.id)}" .',
        f'{_HEADER}seq "{patch.seq}" .',
        f'{_HEADER}time "{patch.timestamp.isoformat()}" .',
        f'{_HEADER}actor "{_escape(patch.actor)}" .',
    ]
    if patch.inverse_of is not None:
        lines.append(f'{_HEADER}inverseOf "{_escape(patch.inverse_of)}" .')
    lines.append(TX_BEGIN)
    lines.extend(f"A {_quad_line(quad)}" for quad in patch.additions)
    lines.extend(f"D {_quad_line(quad)}" for quad in patch.deletions)
    lines.append(TX_COMMIT)
    return "\n".join(lines) + "\n"


def serialize_patches(patches: Iterable[Patch]) -> str:
    return "".join(serialize_patch(patch) for patch in patches)


def _quad_line(quad: Quad) -> str:
    # str() on a pyoxigraph term is its N-Triples form; the graph name is
    # omitted for the default graph, exactly as N-Quads wants it.
    parts = [str(quad.subject), str(quad.predicate), str(quad.object)]
    if not isinstance(quad.graph_name, DefaultGraph):
        parts.append(str(quad.graph_name))
    return " ".join(parts) + " ."


def _parse_quad(line: str, *, line_number: int) -> Quad:
    try:
        parsed = list(parse(line, format=RdfFormat.N_QUADS))
    except (SyntaxError, ValueError) as error:
        raise PatchParseError(f"line {line_number}: unreadable quad: {line!r}") from error
    if len(parsed) != 1:
        raise PatchParseError(f"line {line_number}: expected exactly one quad in {line!r}")
    quad = parsed[0]
    if not isinstance(quad, Quad):  # pragma: no cover - N-Quads always yields quads
        raise PatchParseError(f"line {line_number}: expected a quad in {line!r}")
    return quad


def _parse_header(line: str, *, line_number: int) -> tuple[str, str]:
    body = line[len(_HEADER) :].removesuffix(".").strip()
    name, _, raw_value = body.partition(" ")
    raw_value = raw_value.strip()
    if not name or not raw_value.startswith('"') or not raw_value.endswith('"'):
        raise PatchParseError(f"line {line_number}: malformed header: {line!r}")
    return name, _unescape(raw_value[1:-1])


def _build(headers: dict[str, str], additions: list[Quad], deletions: list[Quad]) -> Patch:
    missing = {"id", "seq", "time", "actor"} - headers.keys()
    if missing:
        raise PatchParseError(f"patch is missing header(s): {', '.join(sorted(missing))}")
    try:
        seq = int(headers["seq"])
        timestamp = datetime.fromisoformat(headers["time"])
    except ValueError as error:
        raise PatchParseError(f"patch {headers['id']} has an unreadable header: {error}") from error
    return Patch(
        id=headers["id"],
        seq=seq,
        timestamp=timestamp,
        actor=headers["actor"],
        additions=tuple(additions),
        deletions=tuple(deletions),
        inverse_of=headers.get("inverseOf"),
    )


def parse_patches(payload: str) -> list[Patch]:
    """Read every patch from an append-only changelog stream."""
    patches: list[Patch] = []
    headers: dict[str, str] = {}
    additions: list[Quad] = []
    deletions: list[Quad] = []
    in_transaction = False

    for line_number, raw in enumerate(payload.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == TX_BEGIN:
            if in_transaction:
                raise PatchParseError(f"line {line_number}: transaction already open")
            in_transaction = True
            continue
        if line == TX_COMMIT:
            if not in_transaction:
                raise PatchParseError(f"line {line_number}: TC without a matching TX")
            patches.append(_build(headers, additions, deletions))
            headers, additions, deletions = {}, [], []
            in_transaction = False
            continue
        if line.startswith(_HEADER):
            if in_transaction:
                raise PatchParseError(f"line {line_number}: header inside a transaction")
            name, value = _parse_header(line, line_number=line_number)
            headers[name] = value
            continue
        if not in_transaction:
            raise PatchParseError(f"line {line_number}: quad outside a transaction")
        operation, _, rest = line.partition(" ")
        if operation == "A":
            additions.append(_parse_quad(rest, line_number=line_number))
        elif operation == "D":
            deletions.append(_parse_quad(rest, line_number=line_number))
        else:
            raise PatchParseError(f"line {line_number}: unknown operation {operation!r}")

    if in_transaction:
        raise PatchParseError("changelog ends inside a transaction: missing TC")
    return patches


def total_size(patches: Sequence[Patch]) -> int:
    return sum(patch.size for patch in patches)
