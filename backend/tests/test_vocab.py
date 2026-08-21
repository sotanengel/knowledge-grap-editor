from __future__ import annotations

import pytest

from ontoforge.runtime import Runtime
from ontoforge.store import graphs
from ontoforge.vocab import loader


def test_every_bundled_vocabulary_ships_with_the_package() -> None:
    assert all(vocabulary.path.is_file() for vocabulary in loader.BUNDLED)


def test_the_vocabularies_the_specification_names_are_all_there() -> None:
    assert {"schema", "skos", "foaf", "dcterms", "prov", "owl", "rdfs"} <= set(loader.BY_NAME)


def test_a_vocabulary_lands_in_its_own_read_only_graph(runtime: Runtime) -> None:
    loaded = loader.load(runtime.store, ["skos"])
    assert loaded["skos"] > 100
    assert runtime.store.count(graphs.vocab_graph("skos")) == loaded["skos"]
    assert runtime.store.count(graphs.DATA) == 0


def test_loading_twice_replaces_rather_than_duplicates(runtime: Runtime) -> None:
    first = loader.load(runtime.store, ["skos"])["skos"]
    loader.load(runtime.store, ["skos"])
    assert runtime.store.count(graphs.vocab_graph("skos")) == first


def test_the_defaults_load_without_touching_the_network(runtime: Runtime) -> None:
    loaded = loader.load(runtime.store, loader.DEFAULT_VOCABULARIES)
    assert set(loaded) == set(loader.DEFAULT_VOCABULARIES)
    assert loader.loaded_names(runtime.store) == sorted(loader.DEFAULT_VOCABULARIES)


def test_schema_org_is_bundled_but_not_loaded_by_default(runtime: Runtime) -> None:
    assert "schema" not in loader.DEFAULT_VOCABULARIES
    assert loader.load(runtime.store, ["schema"])["schema"] > 10_000


def test_an_unknown_vocabulary_is_reported(runtime: Runtime) -> None:
    with pytest.raises(loader.UnknownVocabularyError, match="wingdings"):
        loader.load(runtime.store, ["wingdings"])


def test_the_catalogue_describes_each_vocabulary_for_the_palette() -> None:
    entry = next(item for item in loader.catalogue() if item["name"] == "schema")
    assert entry["prefix"] == "schema"
    assert entry["namespace"] == "https://schema.org/"
    assert entry["licence"]


@pytest.mark.parametrize(
    "url",
    ["https://www.w3.org/ns/prov-o.ttl", "https://schema.org/version/latest/x.ttl"],
)
def test_allow_listed_hosts_may_be_fetched(url: str) -> None:
    assert loader.check_fetch_allowed(url) == url


@pytest.mark.parametrize(
    "url",
    ["https://evil.example/vocab.ttl", "file:///etc/passwd", "http://localhost:8080/x.ttl"],
)
def test_anything_off_the_allow_list_is_refused(url: str) -> None:
    with pytest.raises(ValueError):
        loader.check_fetch_allowed(url)
