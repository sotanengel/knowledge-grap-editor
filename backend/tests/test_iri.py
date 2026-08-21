from __future__ import annotations

import pytest
from pyoxigraph import BlankNode, NamedNode

from ontoforge.store.iri import IriMinter, slugify_term

BASE = "https://example.org/kg/"


@pytest.fixture
def minter() -> IriMinter:
    return IriMinter(BASE)


def test_instance_iris_use_the_base_and_a_ulid(minter: IriMinter) -> None:
    iri = minter.new_instance()
    assert isinstance(iri, NamedNode)
    assert iri.value.startswith(f"{BASE}id/")
    assert len(iri.value.removeprefix(f"{BASE}id/")) == 26


def test_instance_iris_are_unique(minter: IriMinter) -> None:
    minted = {minter.new_instance().value for _ in range(200)}
    assert len(minted) == 200


def test_class_iris_are_pascal_case(minter: IriMinter) -> None:
    assert minter.class_iri("business unit").value == f"{BASE}ont#BusinessUnit"
    assert minter.class_iri("  person  ").value == f"{BASE}ont#Person"


def test_property_iris_are_camel_case(minter: IriMinter) -> None:
    assert minter.property_iri("works for").value == f"{BASE}ont#worksFor"
    assert minter.property_iri("Founded Year").value == f"{BASE}ont#foundedYear"


def test_japanese_labels_are_kept_verbatim_because_iris_allow_them(minter: IriMinter) -> None:
    # RFC 3987 IRIs accept non-ASCII, so a Japanese label needs no transliteration.
    assert minter.class_iri("人物").value == f"{BASE}ont#人物"
    assert minter.property_iri("所属").value == f"{BASE}ont#所属"


def test_characters_illegal_in_an_iri_are_dropped(minter: IriMinter) -> None:
    assert minter.class_iri("Foo <bar> {baz}|qux").value == f"{BASE}ont#FooBarBazQux"


def test_an_unusable_label_falls_back_to_a_generated_term(minter: IriMinter) -> None:
    iri = minter.class_iri("<<< >>>")
    assert iri.value.startswith(f"{BASE}ont#Term")


def test_slugify_term_is_pure() -> None:
    assert slugify_term("hello world", style="pascal") == "HelloWorld"
    assert slugify_term("hello world", style="camel") == "helloWorld"
    assert slugify_term("HTTP server", style="pascal") == "HTTPServer"


def test_minting_never_reuses_an_instance_iri_for_a_relabelled_node(minter: IriMinter) -> None:
    # IRIs are immutable: renaming is an rdfs:label change, never a re-mint.
    first = minter.new_instance()
    assert minter.new_instance() != first


def test_skolemise_turns_a_blank_node_into_a_stable_iri(minter: IriMinter) -> None:
    blank = BlankNode("b0")
    iri = minter.skolemize(blank)
    assert iri.value == f"{BASE}.well-known/genid/b0"
    assert minter.skolemize(blank) == iri


def test_base_iri_without_trailing_separator_is_normalised() -> None:
    assert IriMinter("https://example.org/kg").new_instance().value.startswith(f"{BASE}id/")


def test_ontology_namespace_is_exposed(minter: IriMinter) -> None:
    assert minter.ontology_namespace == f"{BASE}ont#"
