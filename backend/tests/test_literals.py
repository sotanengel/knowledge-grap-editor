from __future__ import annotations

import pytest
from pyoxigraph import Literal, NamedNode

from ontoforge.literals import (
    XSD_BOOLEAN,
    XSD_DATE,
    XSD_DATETIME,
    XSD_DECIMAL,
    XSD_INTEGER,
    XSD_STRING,
    infer_datatype,
    make_literal,
    term_from_json,
    term_to_json,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("42", XSD_INTEGER),
        ("-7", XSD_INTEGER),
        ("3.5", XSD_DECIMAL),
        ("true", XSD_BOOLEAN),
        ("FALSE", XSD_BOOLEAN),
        ("2026-08-21", XSD_DATE),
        ("2026-08-21T09:00:00Z", XSD_DATETIME),
        ("2026-08-21T09:00:00+09:00", XSD_DATETIME),
        ("こんにちは", XSD_STRING),
        ("", XSD_STRING),
        ("007-A", XSD_STRING),
    ],
)
def test_datatype_inference(text: str, expected: NamedNode) -> None:
    assert infer_datatype(text) == expected


def test_an_explicit_datatype_wins_over_inference() -> None:
    literal = make_literal("42", datatype=XSD_STRING)
    assert literal.datatype == XSD_STRING
    assert literal.value == "42"


def test_a_language_tag_produces_a_language_literal() -> None:
    literal = make_literal("田中太郎", language="ja")
    assert literal.language == "ja"


def test_a_language_tag_and_a_datatype_together_are_rejected() -> None:
    with pytest.raises(ValueError, match="language"):
        make_literal("x", datatype=XSD_STRING, language="ja")


def test_python_scalars_map_to_their_xsd_types() -> None:
    assert make_literal(42).datatype == XSD_INTEGER
    assert make_literal(3.5).datatype == XSD_DECIMAL
    assert make_literal(True).datatype == XSD_BOOLEAN


def test_a_value_that_does_not_fit_its_declared_datatype_is_rejected() -> None:
    with pytest.raises(ValueError, match="xsd:integer"):
        make_literal("not a number", datatype=XSD_INTEGER)


def test_terms_round_trip_through_json() -> None:
    for term in (
        NamedNode("https://example.org/kg/id/1"),
        Literal("田中太郎", language="ja"),
        Literal("42", datatype=XSD_INTEGER),
        Literal("plain", datatype=XSD_STRING),
    ):
        assert term_from_json(term_to_json(term)) == term


def test_named_nodes_serialise_as_id_objects() -> None:
    assert term_to_json(NamedNode("https://x/1")) == {"@id": "https://x/1"}


def test_literals_serialise_as_value_objects() -> None:
    assert term_to_json(Literal("42", datatype=XSD_INTEGER)) == {
        "@value": "42",
        "@type": XSD_INTEGER.value,
    }
    assert term_to_json(Literal("あ", language="ja")) == {"@value": "あ", "@language": "ja"}


def test_a_bare_json_scalar_is_accepted_as_a_literal() -> None:
    assert term_from_json("hello") == Literal("hello", datatype=XSD_STRING)
    assert term_from_json(42) == Literal("42", datatype=XSD_INTEGER)


def test_an_unusable_json_payload_is_rejected() -> None:
    with pytest.raises(ValueError, match="term"):
        term_from_json({"unexpected": "shape"})
