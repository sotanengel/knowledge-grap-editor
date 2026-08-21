from __future__ import annotations

from pathlib import Path

import pytest

from ontoforge.search.fts import SearchIndex, SearchRecord


@pytest.fixture
def index(tmp_path: Path) -> SearchIndex:
    with SearchIndex(tmp_path / "index") as opened:
        yield opened


def _record(iri: str, label: str, comment: str = "", types: tuple[str, ...] = ()) -> SearchRecord:
    return SearchRecord(iri=iri, label=label, comment=comment, types=types)


def test_a_record_can_be_found_by_a_word_in_its_label(index: SearchIndex) -> None:
    index.upsert(_record("iri:1", "ACME Corporation"))
    assert [hit.iri for hit in index.search("acme")] == ["iri:1"]


def test_japanese_labels_are_searchable_including_short_queries(index: SearchIndex) -> None:
    index.upsert(_record("iri:1", "田中太郎"))
    index.upsert(_record("iri:2", "株式会社アクメ"))
    assert [hit.iri for hit in index.search("田中太郎")] == ["iri:1"]
    assert [hit.iri for hit in index.search("田中")] == ["iri:1"]
    assert [hit.iri for hit in index.search("アクメ")] == ["iri:2"]


def test_the_comment_is_searched_too(index: SearchIndex) -> None:
    index.upsert(_record("iri:1", "田中太郎", comment="アクメの社員"))
    assert [hit.iri for hit in index.search("社員")] == ["iri:1"]


def test_results_can_be_narrowed_to_a_type(index: SearchIndex) -> None:
    index.upsert(_record("iri:1", "田中太郎", types=("ont:Person",)))
    index.upsert(_record("iri:2", "田中商店", types=("ont:Organization",)))
    assert [hit.iri for hit in index.search("田中", type_iri="ont:Person")] == ["iri:1"]


def test_an_empty_query_lists_everything(index: SearchIndex) -> None:
    index.upsert(_record("iri:1", "a"))
    index.upsert(_record("iri:2", "b"))
    assert len(index.search("")) == 2


def test_results_are_paged(index: SearchIndex) -> None:
    for n in range(10):
        index.upsert(_record(f"iri:{n}", f"node {n}"))
    assert len(index.search("", limit=3)) == 3
    assert len(index.search("", limit=3, offset=9)) == 1


def test_upsert_replaces_rather_than_duplicates(index: SearchIndex) -> None:
    index.upsert(_record("iri:1", "old name"))
    index.upsert(_record("iri:1", "new name"))
    assert index.count() == 1
    assert index.search("old") == []
    assert [hit.iri for hit in index.search("new")] == ["iri:1"]


def test_delete_removes_a_record(index: SearchIndex) -> None:
    index.upsert(_record("iri:1", "田中太郎"))
    index.delete("iri:1")
    assert index.search("田中") == []


def test_hits_carry_the_label_and_types(index: SearchIndex) -> None:
    index.upsert(_record("iri:1", "田中太郎", comment="社員", types=("ont:Person",)))
    (hit,) = index.search("田中")
    assert hit.label == "田中太郎"
    assert hit.comment == "社員"
    assert hit.types == ("ont:Person",)


def test_the_index_survives_a_reopen(tmp_path: Path) -> None:
    with SearchIndex(tmp_path / "index") as first:
        first.upsert(_record("iri:1", "田中太郎"))
    with SearchIndex(tmp_path / "index") as second:
        assert [hit.iri for hit in second.search("田中")] == ["iri:1"]


def test_clear_empties_the_index(index: SearchIndex) -> None:
    index.upsert(_record("iri:1", "a"))
    index.clear()
    assert index.count() == 0


def test_replace_all_rebuilds_the_index_in_one_go(index: SearchIndex) -> None:
    index.upsert(_record("iri:old", "gone"))
    index.replace_all([_record("iri:1", "田中太郎"), _record("iri:2", "アクメ")])
    assert index.count() == 2
    assert index.search("gone") == []


def test_a_query_full_of_punctuation_does_not_explode(index: SearchIndex) -> None:
    index.upsert(_record("iri:1", "ACME"))
    assert index.search('"*(){}[]^') == []


# ---------------------------------------------------------------- instances vs terms


def test_records_can_be_separated_into_instances_and_terms(index: SearchIndex) -> None:
    index.upsert(SearchRecord(iri="iri:1", label="田中太郎", kind="instance"))
    index.upsert(SearchRecord(iri="iri:2", label="人物", kind="term"))
    assert [hit.iri for hit in index.search("", kind="instance")] == ["iri:1"]
    assert [hit.iri for hit in index.search("", kind="term")] == ["iri:2"]
    assert len(index.search("")) == 2


def test_records_default_to_being_instances(index: SearchIndex) -> None:
    index.upsert(_record("iri:1", "田中太郎"))
    (hit,) = index.search("田中")
    assert hit.kind == "instance"


def test_the_kind_filter_combines_with_the_query(index: SearchIndex) -> None:
    index.upsert(SearchRecord(iri="iri:1", label="人物", kind="term"))
    index.upsert(SearchRecord(iri="iri:2", label="人物ではない", kind="instance"))
    assert [hit.iri for hit in index.search("人物", kind="term")] == ["iri:1"]


def test_an_index_from_an_older_schema_is_rebuilt_rather_than_migrated(tmp_path: Path) -> None:
    import sqlite3

    directory = tmp_path / "index"
    directory.mkdir()
    with sqlite3.connect(directory / "search.sqlite3") as legacy:
        legacy.execute(
            "CREATE VIRTUAL TABLE entities USING fts5("
            "iri UNINDEXED, label, comment, types UNINDEXED, tokenize='trigram')"
        )
        legacy.execute("INSERT INTO entities VALUES ('iri:old', 'old', '', '')")

    with SearchIndex(directory) as rebuilt:
        # The index is a cache: dropping it is safe, and the runtime repopulates it.
        assert rebuilt.stale
        rebuilt.upsert(_record("iri:1", "田中太郎"))
        assert [hit.iri for hit in rebuilt.search("田中")] == ["iri:1"]


def test_reopening_a_current_index_keeps_its_contents(tmp_path: Path) -> None:
    directory = tmp_path / "index"
    with SearchIndex(directory) as first:
        first.upsert(_record("iri:1", "田中太郎"))
    with SearchIndex(directory) as second:
        assert not second.stale
        assert [hit.iri for hit in second.search("田中")] == ["iri:1"]
