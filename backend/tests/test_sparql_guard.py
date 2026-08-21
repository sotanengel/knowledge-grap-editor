from __future__ import annotations

import pytest

from ontoforge.sparql.guard import (
    UPDATE_KEYWORDS,
    QueryForm,
    SparqlRejectedError,
    ensure_read_only,
    query_form,
    strip_comments_and_strings,
)

SELECT = "SELECT ?s WHERE { ?s ?p ?o }"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (SELECT, QueryForm.SELECT),
        ("select ?s where { ?s ?p ?o }", QueryForm.SELECT),
        ("ASK { ?s ?p ?o }", QueryForm.ASK),
        ("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }", QueryForm.CONSTRUCT),
        ("DESCRIBE <https://example.org/kg/id/1>", QueryForm.DESCRIBE),
        ("PREFIX ex: <https://example.org/> SELECT ?s WHERE { ?s ?p ?o }", QueryForm.SELECT),
        ("BASE <https://example.org/>\n# a comment\nASK { ?s ?p ?o }", QueryForm.ASK),
    ],
)
def test_read_only_forms_are_recognised(query: str, expected: QueryForm) -> None:
    assert query_form(query) == expected
    assert ensure_read_only(query) == expected


@pytest.mark.parametrize(
    "query",
    [
        "INSERT DATA { <https://a> <https://b> <https://c> }",
        "insert data { <https://a> <https://b> <https://c> }",
        "DELETE WHERE { ?s ?p ?o }",
        "DELETE DATA { <https://a> <https://b> <https://c> }",
        "LOAD <https://example.org/evil.ttl>",
        "CLEAR ALL",
        "DROP GRAPH <urn:ontoforge:data>",
        "CREATE GRAPH <urn:ontoforge:data>",
        "COPY DEFAULT TO <urn:ontoforge:data>",
        "MOVE DEFAULT TO <urn:ontoforge:data>",
        "ADD DEFAULT TO <urn:ontoforge:data>",
        "WITH <urn:ontoforge:data> DELETE { ?s ?p ?o } WHERE { ?s ?p ?o }",
    ],
)
def test_update_operations_are_rejected(query: str) -> None:
    with pytest.raises(SparqlRejectedError):
        ensure_read_only(query)


def test_an_update_smuggled_after_a_valid_query_is_rejected() -> None:
    with pytest.raises(SparqlRejectedError):
        ensure_read_only(f"{SELECT} ; INSERT DATA {{ <https://a> <https://b> <https://c> }}")


def test_the_word_insert_inside_a_comment_is_harmless() -> None:
    query = f"# INSERT DATA is not happening here\n{SELECT}"
    assert ensure_read_only(query) == QueryForm.SELECT


def test_the_word_delete_inside_a_string_literal_is_harmless() -> None:
    query = 'SELECT ?s WHERE { ?s ?p "DELETE WHERE { ?a ?b ?c }" }'
    assert ensure_read_only(query) == QueryForm.SELECT


def test_a_keyword_inside_a_long_string_literal_is_harmless() -> None:
    query = 'SELECT ?s WHERE { ?s ?p """LOAD <https://evil>""" }'
    assert ensure_read_only(query) == QueryForm.SELECT


def test_a_keyword_inside_an_iri_is_harmless() -> None:
    query = "SELECT ?s WHERE { ?s ?p <https://example.org/DROP/CLEAR> }"
    assert ensure_read_only(query) == QueryForm.SELECT


def test_a_keyword_that_is_only_part_of_a_longer_word_is_harmless() -> None:
    assert ensure_read_only("SELECT ?insertion WHERE { ?insertion ?p ?o }") == QueryForm.SELECT


def test_an_escaped_quote_does_not_end_a_string_early() -> None:
    query = 'SELECT ?s WHERE { ?s ?p "he said \\" DROP GRAPH <x> " }'
    assert ensure_read_only(query) == QueryForm.SELECT


def test_a_query_with_no_recognisable_form_is_rejected() -> None:
    with pytest.raises(SparqlRejectedError, match="form"):
        ensure_read_only("PREFIX ex: <https://example.org/>")


def test_an_empty_query_is_rejected() -> None:
    with pytest.raises(SparqlRejectedError):
        ensure_read_only("   ")


def test_stripping_removes_comments_strings_and_iris_but_keeps_offsets() -> None:
    source = 'SELECT ?s WHERE { ?s <https://x#DROP> "CLEAR" } # LOAD'
    stripped = strip_comments_and_strings(source)
    assert len(stripped) == len(source)
    assert "DROP" not in stripped
    assert "CLEAR" not in stripped
    assert "LOAD" not in stripped
    assert "SELECT" in stripped


def test_every_sparql_update_keyword_is_covered() -> None:
    assert {
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
    } <= UPDATE_KEYWORDS
