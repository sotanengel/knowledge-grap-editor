"""Reject SPARQL Update on the read paths (§9.2, §13).

This is the third of the three defences that keep AI clients from writing to the
graph. The other two are structural -- no update tool exists, and the MCP process
opens the store with a read-only handle -- but a ``sparql_select`` tool still
takes arbitrary query text, so that text has to be checked.

Checking with a regular expression over the raw query would be wrong in both
directions: ``# INSERT`` in a comment is harmless, and a literal containing
``"DELETE"`` is harmless, while an update hidden after a ``;`` is not. So the
query is first stripped of everything that is not code -- comments, string
literals of all four SPARQL flavours, and IRI references -- with offsets
preserved, and only then scanned for update keywords.
"""

from __future__ import annotations

import re
from enum import StrEnum

_BLANK = " "


class QueryForm(StrEnum):
    """The four read-only SPARQL query forms."""

    SELECT = "SELECT"
    ASK = "ASK"
    CONSTRUCT = "CONSTRUCT"
    DESCRIBE = "DESCRIBE"


#: Every keyword that can start (or scope) a SPARQL 1.1 Update operation.
UPDATE_KEYWORDS: frozenset[str] = frozenset(
    {
        "INSERT",
        "DELETE",
        "LOAD",
        "CLEAR",
        "DROP",
        "CREATE",
        "ADD",
        "MOVE",
        "COPY",
        "WITH",
    }
)

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LONG_QUOTES = ('"""', "'''")
_SHORT_QUOTES = ('"', "'")


class SparqlRejectedError(ValueError):
    """Raised when a query may not run on a read-only endpoint."""


def strip_comments_and_strings(query: str) -> str:
    """Blank out comments, string literals and IRIs, keeping the string's length.

    Offsets survive so that any error can still point at the original text.
    """
    out: list[str] = []
    index = 0
    length = len(query)

    while index < length:
        character = query[index]

        if character == "#":
            end = query.find("\n", index)
            end = length if end == -1 else end
            out.append(_BLANK * (end - index))
            index = end
            continue

        if character == "<":
            iri_end = _end_of_iri(query, index)
            if iri_end is not None:
                out.append(_BLANK * (iri_end - index))
                index = iri_end
                continue

        long_quote = next((q for q in _LONG_QUOTES if query.startswith(q, index)), None)
        if long_quote is not None:
            end = _end_of_string(query, index + 3, long_quote)
            out.append(_BLANK * (end - index))
            index = end
            continue

        if character in _SHORT_QUOTES:
            end = _end_of_string(query, index + 1, character)
            out.append(_BLANK * (end - index))
            index = end
            continue

        out.append(character)
        index += 1

    return "".join(out)


def _end_of_iri(query: str, start: int) -> int | None:
    """Index just past the closing ``>``, or ``None`` if this is not an IRI."""
    index = start + 1
    while index < len(query):
        character = query[index]
        if character == ">":
            return index + 1
        # An IRIREF may not contain whitespace or these delimiters; if one turns
        # up, the '<' was a comparison operator rather than the start of an IRI.
        if character in ' \t\n\r<"{}|^`\\':
            return None
        index += 1
    return None


def _end_of_string(query: str, start: int, quote: str) -> int:
    """Index just past the closing quote, or the end of input if it never closes."""
    index = start
    while index < len(query):
        if query[index] == "\\":
            index += 2
            continue
        if query.startswith(quote, index):
            return index + len(quote)
        index += 1
    return len(query)


def _keywords(code: str) -> list[str]:
    return [match.group(0).upper() for match in _WORD.finditer(code)]


def query_form(query: str) -> QueryForm | None:
    """The form of ``query``, ignoring ``BASE`` / ``PREFIX`` declarations."""
    code = strip_comments_and_strings(query)
    skip_next = False
    for word in _keywords(code):
        if skip_next:
            # The token after PREFIX is the prefix label, not a query form.
            skip_next = False
            continue
        if word == "PREFIX":
            skip_next = True
            continue
        if word == "BASE":
            continue
        if word in QueryForm.__members__:
            return QueryForm[word]
        return None
    return None


def ensure_read_only(query: str) -> QueryForm:
    """Return the query form, or raise if ``query`` could change the graph."""
    code = strip_comments_and_strings(query)
    if not code.strip():
        raise SparqlRejectedError("the query is empty")

    found = sorted(UPDATE_KEYWORDS.intersection(_keywords(code)))
    if found:
        raise SparqlRejectedError(
            "this endpoint is read-only; the query uses SPARQL Update "
            f"keyword(s): {', '.join(found)}"
        )

    form = query_form(query)
    if form is None:
        raise SparqlRejectedError(
            "the query has no recognisable form; expected SELECT, ASK, CONSTRUCT or DESCRIBE"
        )
    return form


def is_read_only(query: str) -> bool:
    """Whether ``query`` is safe for a read-only endpoint."""
    try:
        ensure_read_only(query)
    except SparqlRejectedError:
        return False
    return True
