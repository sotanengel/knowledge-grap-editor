"""Literal handling: type inference, and the JSON shape terms take on the wire.

The user is never asked to write ``"42"^^xsd:integer``. They type a value, the
system guesses the type, and the inspector shows that guess in a dropdown they
can correct (§4.3).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from pyoxigraph import BlankNode, Literal, NamedNode, Triple

from ontoforge.namespaces import XSD

XSD_STRING = NamedNode(f"{XSD}string")
XSD_INTEGER = NamedNode(f"{XSD}integer")
XSD_DECIMAL = NamedNode(f"{XSD}decimal")
XSD_DOUBLE = NamedNode(f"{XSD}double")
XSD_BOOLEAN = NamedNode(f"{XSD}boolean")
XSD_DATE = NamedNode(f"{XSD}date")
XSD_DATETIME = NamedNode(f"{XSD}dateTime")

#: The types the inspector offers, in the order it offers them.
OFFERED_DATATYPES = (
    XSD_STRING,
    XSD_INTEGER,
    XSD_DECIMAL,
    XSD_BOOLEAN,
    XSD_DATE,
    XSD_DATETIME,
)

_INTEGER = re.compile(r"^[+-]?\d+$")
_DECIMAL = re.compile(r"^[+-]?(\d+\.\d*|\.\d+)$")
_BOOLEAN = frozenset({"true", "false"})


def infer_datatype(text: str) -> NamedNode:
    """Guess the XSD type of a value the user typed."""
    stripped = text.strip()
    if not stripped:
        return XSD_STRING
    if stripped.lower() in _BOOLEAN:
        return XSD_BOOLEAN
    if _INTEGER.match(stripped):
        return XSD_INTEGER
    if _DECIMAL.match(stripped):
        return XSD_DECIMAL
    if _is_date(stripped):
        return XSD_DATE
    if _is_datetime(stripped):
        return XSD_DATETIME
    return XSD_STRING


def _is_date(text: str) -> bool:
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _is_datetime(text: str) -> bool:
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _check(text: str, datatype: NamedNode) -> None:
    """Reject a value that cannot possibly hold its declared type."""
    if datatype == XSD_INTEGER and not _INTEGER.match(text.strip()):
        raise ValueError(f"{text!r} is not a valid xsd:integer")
    if datatype in (XSD_DECIMAL, XSD_DOUBLE) and not (
        _INTEGER.match(text.strip()) or _DECIMAL.match(text.strip())
    ):
        raise ValueError(f"{text!r} is not a valid {datatype.value.rsplit('#', 1)[-1]}")
    if datatype == XSD_BOOLEAN and text.strip().lower() not in _BOOLEAN:
        raise ValueError(f"{text!r} is not a valid xsd:boolean")
    if datatype == XSD_DATE and not _is_date(text.strip()):
        raise ValueError(f"{text!r} is not a valid xsd:date")
    if datatype == XSD_DATETIME and not _is_datetime(text.strip()):
        raise ValueError(f"{text!r} is not a valid xsd:dateTime")


def make_literal(
    value: str | int | float | bool,
    *,
    datatype: NamedNode | None = None,
    language: str | None = None,
) -> Literal:
    """Build a literal from a user-supplied value."""
    if language is not None and datatype is not None:
        raise ValueError("a literal cannot carry both a language tag and a datatype")

    if isinstance(value, bool):
        return Literal("true" if value else "false", datatype=XSD_BOOLEAN)
    if isinstance(value, int):
        return Literal(str(value), datatype=XSD_INTEGER)
    if isinstance(value, float):
        return Literal(repr(value), datatype=XSD_DECIMAL)

    if language is not None:
        return Literal(value, language=language)
    resolved = datatype if datatype is not None else infer_datatype(value)
    _check(value, resolved)
    return Literal(value, datatype=resolved)


def term_to_json(term: Any) -> dict[str, Any]:
    """Render a term as the JSON-LD node or value object for it."""
    if isinstance(term, NamedNode):
        return {"@id": term.value}
    if isinstance(term, BlankNode):
        return {"@id": f"_:{term.value}"}
    if isinstance(term, Literal):
        if term.language:
            return {"@value": term.value, "@language": term.language}
        return {"@value": term.value, "@type": term.datatype.value}
    if isinstance(term, Triple):
        return {
            "@quotedTriple": [
                term_to_json(term.subject),
                term_to_json(term.predicate),
                term_to_json(term.object),
            ]
        }
    raise ValueError(f"cannot serialise term of type {type(term).__name__}")


def term_from_json(payload: Any) -> Any:
    """Read back what :func:`term_to_json` wrote, or a bare JSON scalar."""
    if isinstance(payload, str | int | float | bool):
        return make_literal(payload)
    if not isinstance(payload, dict):
        raise ValueError(f"cannot read a term from {type(payload).__name__}")

    if "@id" in payload:
        iri = str(payload["@id"])
        return BlankNode(iri.removeprefix("_:")) if iri.startswith("_:") else NamedNode(iri)
    if "@value" in payload:
        value = payload["@value"]
        language = payload.get("@language")
        datatype = payload.get("@type")
        return make_literal(
            value if isinstance(value, str | int | float | bool) else str(value),
            datatype=NamedNode(datatype) if datatype else None,
            language=language,
        )
    if "@quotedTriple" in payload:
        subject, predicate, obj = payload["@quotedTriple"]
        return Triple(term_from_json(subject), term_from_json(predicate), term_from_json(obj))
    raise ValueError(f"cannot read a term from {sorted(payload)}")


def literal_value(term: Any) -> str:
    """The plain text of a term, for indexing and display."""
    if isinstance(term, Literal):
        return term.value
    if isinstance(term, NamedNode):
        return term.value
    return str(term)
