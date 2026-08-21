from __future__ import annotations

from pathlib import Path

import pytest

from ontoforge.semantic.embedder import HashingEmbedder
from ontoforge.semantic.vectors import VectorIndex


@pytest.fixture
def index(tmp_path: Path) -> VectorIndex:
    with VectorIndex(tmp_path / "index", embedder=HashingEmbedder()) as opened:
        yield opened


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
    with VectorIndex(tmp_path / "index", embedder=HashingEmbedder()) as first:
        first.upsert("iri:1", "田中太郎")
    with VectorIndex(tmp_path / "index", embedder=HashingEmbedder()) as second:
        assert [hit.iri for hit in second.search("田中")] == ["iri:1"]


def test_an_empty_query_returns_nothing(index: VectorIndex) -> None:
    index.upsert("iri:1", "田中太郎")
    assert index.search("  ") == []


def test_the_limit_is_honoured(index: VectorIndex) -> None:
    for n in range(20):
        index.upsert(f"iri:{n}", f"田中{n}")
    assert len(index.search("田中", limit=5)) == 5


# ---------------------------------------------------------------- the embedder behind it


def test_the_index_records_which_embedder_filled_it(tmp_path: Path) -> None:
    from ontoforge.semantic.embedder import HashingEmbedder

    with VectorIndex(tmp_path / "index", embedder=HashingEmbedder()) as index:
        assert index.embedder.quality == "surface"
        assert index.dimensions == index.embedder.dimensions


def test_changing_the_embedder_rebuilds_rather_than_mixing_vectors(tmp_path: Path) -> None:
    """Vectors from two different embedders are not comparable at all.

    Keeping them side by side would produce silent nonsense, so a change empties
    the index and the runtime refills it.
    """
    from ontoforge.semantic.embedder import HashingEmbedder

    directory = tmp_path / "index"
    with VectorIndex(directory, embedder=HashingEmbedder(dimensions=512)) as first:
        first.upsert("iri:1", "田中太郎")
        assert first.count() == 1

    with VectorIndex(directory, embedder=HashingEmbedder(dimensions=256)) as second:
        assert second.stale
        assert second.count() == 0


def test_the_same_embedder_keeps_the_index(tmp_path: Path) -> None:
    from ontoforge.semantic.embedder import HashingEmbedder

    directory = tmp_path / "index"
    with VectorIndex(directory, embedder=HashingEmbedder()) as first:
        first.upsert("iri:1", "田中太郎")
    with VectorIndex(directory, embedder=HashingEmbedder()) as second:
        assert not second.stale
        assert [hit.iri for hit in second.search("田中")] == ["iri:1"]


@pytest.mark.skipif(
    not __import__(
        "ontoforge.semantic.embedder", fromlist=["model_is_available"]
    ).model_is_available(
        __import__(
            "ontoforge.semantic.embedder", fromlist=["default_model_dir"]
        ).default_model_dir()
    ),
    reason="the embedding model is fetched at build time",
)
def test_with_the_model_a_search_finds_what_shares_no_character(tmp_path: Path) -> None:
    """The whole point: 「企業」 finds 「株式会社アクメ」.

    Not one character is shared, so the surface fallback scores this at zero.
    """
    from ontoforge.semantic.embedder import StaticEmbedder, default_model_dir

    with VectorIndex(tmp_path / "index", embedder=StaticEmbedder(default_model_dir())) as index:
        index.replace_all(
            [
                ("iri:acme", "株式会社アクメ"),
                ("iri:alice", "田中太郎"),
                ("iri:apple", "りんご"),
            ]
        )
        top = index.search("企業", limit=3)
        assert top[0].iri == "iri:acme", top
        assert top[0].score > 0
