from __future__ import annotations

from pathlib import Path

import pytest

from ontoforge.semantic.vectors import VectorIndex, cosine, embed, ngrams, normalise


@pytest.fixture
def index(tmp_path: Path) -> VectorIndex:
    with VectorIndex(tmp_path / "index") as opened:
        yield opened


# ---------------------------------------------------------------- vectors


def test_normalisation_folds_width_and_case() -> None:
    assert normalise("ＡＢＣ") == "abc"
    assert normalise("  a   b  ") == "a b"


def test_ngrams_cover_short_strings_too() -> None:
    assert ngrams("a") == ["a", "a"]
    assert "田中" in ngrams("田中太郎")


def test_a_vector_is_unit_length() -> None:
    vector = embed("田中太郎")
    assert abs(sum(value * value for value in vector) - 1.0) < 1e-6


def test_an_empty_string_gives_a_zero_vector() -> None:
    assert not any(embed("   "))


def test_the_same_text_always_gives_the_same_vector() -> None:
    # A salted hash would make the index unusable across restarts.
    assert embed("田中太郎") == embed("田中太郎")


def test_similar_text_scores_higher_than_unrelated_text() -> None:
    target = embed("田中太郎")
    assert cosine(target, embed("田中太一")) > cosine(target, embed("株式会社アクメ"))


def test_identical_text_scores_one() -> None:
    assert cosine(embed("acme"), embed("ACME")) == pytest.approx(1.0, abs=1e-6)


# ---------------------------------------------------------------- index


def test_a_partial_label_finds_the_whole_one(index: VectorIndex) -> None:
    index.upsert("iri:1", "田中太郎")
    index.upsert("iri:2", "株式会社アクメ")
    assert next(hit.iri for hit in index.search("田中")) == "iri:1"


def test_results_come_back_nearest_first(index: VectorIndex) -> None:
    index.upsert("iri:1", "株式会社アクメ")
    index.upsert("iri:2", "田中太郎")
    index.upsert("iri:3", "田中太一")
    assert [hit.iri for hit in index.search("田中太郎", limit=2)] == ["iri:2", "iri:3"]


def test_nothing_related_comes_back_empty(index: VectorIndex) -> None:
    index.upsert("iri:1", "田中太郎")
    assert index.search("zzzzz", threshold=0.2) == []


def test_upsert_replaces_rather_than_duplicates(index: VectorIndex) -> None:
    index.upsert("iri:1", "古い名前")
    index.upsert("iri:1", "新しい名前")
    assert index.count() == 1
    assert index.search("新しい")[0].label == "新しい名前"


def test_delete_removes_an_entry(index: VectorIndex) -> None:
    index.upsert("iri:1", "田中太郎")
    index.delete("iri:1")
    assert index.count() == 0


def test_replace_all_rebuilds_in_one_go(index: VectorIndex) -> None:
    index.upsert("iri:old", "消える")
    assert index.replace_all([("iri:1", "田中太郎"), ("iri:2", "アクメ")]) == 2
    assert index.count() == 2


def test_the_index_survives_a_reopen(tmp_path: Path) -> None:
    with VectorIndex(tmp_path / "index") as first:
        first.upsert("iri:1", "田中太郎")
    with VectorIndex(tmp_path / "index") as second:
        assert [hit.iri for hit in second.search("田中")] == ["iri:1"]


def test_an_empty_query_returns_nothing(index: VectorIndex) -> None:
    index.upsert("iri:1", "田中太郎")
    assert index.search("  ") == []


def test_the_limit_is_honoured(index: VectorIndex) -> None:
    for n in range(20):
        index.upsert(f"iri:{n}", f"田中{n}")
    assert len(index.search("田中", limit=5)) == 5
