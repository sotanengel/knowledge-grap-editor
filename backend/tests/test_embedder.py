"""Turning text into a vector, and being clear about which kind of vector it is."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ontoforge.semantic.embedder import (
    Embedder,
    HashingEmbedder,
    StaticEmbedder,
    cosine,
    load_embedder,
    model_is_available,
)

MODEL_DIR = Path(__file__).resolve().parents[1] / "src" / "ontoforge" / "semantic" / "model"
needs_model = pytest.mark.skipif(
    not model_is_available(MODEL_DIR), reason="the embedding model is fetched at build time"
)


@pytest.fixture
def hashing() -> HashingEmbedder:
    return HashingEmbedder()


# ---------------------------------------------------------------- both kinds


def _check_contract(embedder: Embedder) -> None:
    vector = embedder.embed("田中太郎")
    assert len(vector) == embedder.dimensions
    assert abs(sum(value * value for value in vector) - 1.0) < 1e-5
    assert embedder.embed("田中太郎") == vector
    assert not any(embedder.embed("   "))


def test_the_fallback_honours_the_contract(hashing: HashingEmbedder) -> None:
    _check_contract(hashing)


@needs_model
def test_the_model_honours_the_contract() -> None:
    _check_contract(StaticEmbedder(MODEL_DIR))


def test_cosine_of_a_vector_with_itself_is_one(hashing: HashingEmbedder) -> None:
    vector = hashing.embed("田中太郎")
    assert cosine(vector, vector) == pytest.approx(1.0, abs=1e-6)


def test_cosine_of_nothing_is_zero(hashing: HashingEmbedder) -> None:
    assert cosine(hashing.embed("  "), hashing.embed("田中")) == 0.0


# ---------------------------------------------------------------- what each is good at


def test_the_fallback_matches_shared_characters(hashing: HashingEmbedder) -> None:
    target = hashing.embed("田中太郎")
    assert cosine(target, hashing.embed("田中太一")) > cosine(target, hashing.embed("株式会社"))


def test_the_fallback_cannot_see_meaning(hashing: HashingEmbedder) -> None:
    """This is why it is only a fallback, and why the interface says so.

    「会社」 and 「企業」 mean nearly the same thing and share no character, so a
    surface measure scores them at zero.
    """
    assert cosine(hashing.embed("会社"), hashing.embed("企業")) == pytest.approx(0.0, abs=1e-6)


@needs_model
def test_the_model_sees_meaning_where_no_character_is_shared() -> None:
    """The point of the whole exercise."""
    embedder = StaticEmbedder(MODEL_DIR)
    related = cosine(embedder.embed("会社"), embedder.embed("企業"))
    unrelated = cosine(embedder.embed("会社"), embedder.embed("果物"))
    assert related > 0.3
    assert related > unrelated


@needs_model
@pytest.mark.parametrize(
    ("left", "right", "other"),
    [("人物", "人間", "自動車"), ("従業員", "社員", "天気"), ("東京", "大阪", "きゅうり")],
)
def test_the_model_ranks_related_words_above_unrelated_ones(
    left: str, right: str, other: str
) -> None:
    embedder = StaticEmbedder(MODEL_DIR)
    target = embedder.embed(left)
    assert cosine(target, embedder.embed(right)) > cosine(target, embedder.embed(other))


# ---------------------------------------------------------------- saying which is which


def test_the_fallback_admits_it_is_a_surface_measure(hashing: HashingEmbedder) -> None:
    assert hashing.quality == "surface"
    assert "意味" in hashing.note


@needs_model
def test_the_model_reports_itself_as_semantic() -> None:
    embedder = StaticEmbedder(MODEL_DIR)
    assert embedder.quality == "semantic"
    assert "potion" in embedder.name


def test_loading_falls_back_when_no_model_is_present(tmp_path: Path) -> None:
    embedder = load_embedder(tmp_path / "absent")
    assert isinstance(embedder, HashingEmbedder)
    assert embedder.quality == "surface"


@needs_model
def test_loading_prefers_the_model_when_it_is_there() -> None:
    assert isinstance(load_embedder(MODEL_DIR), StaticEmbedder)


def test_an_incomplete_model_directory_is_not_mistaken_for_a_model(tmp_path: Path) -> None:
    directory = tmp_path / "model"
    directory.mkdir()
    (directory / "meta.json").write_text(json.dumps({"dimensions": 128}), encoding="utf-8")
    assert not model_is_available(directory)
    assert isinstance(load_embedder(directory), HashingEmbedder)


# ---------------------------------------------------------------- the two side by side


@needs_model
@pytest.mark.parametrize(
    ("query", "wanted", "distractor"),
    [
        ("企業", "株式会社アクメ", "りんご"),
        ("くだもの", "りんご", "株式会社アクメ"),
        ("人", "田中太郎", "会議室A"),
    ],
)
def test_the_model_retrieves_where_the_fallback_cannot(
    query: str, wanted: str, distractor: str
) -> None:
    """Side by side, on the task the feature exists for.

    None of these queries shares a character with its answer, so the surface
    measure scores both candidates at zero and has nothing to rank on. This is
    the difference the model is carried for.
    """
    model = StaticEmbedder(MODEL_DIR)
    surface = HashingEmbedder()

    def better(embedder: Embedder) -> bool:
        target = embedder.embed(query)
        return cosine(target, embedder.embed(wanted)) > cosine(target, embedder.embed(distractor))

    assert better(model), f"the model failed to rank {wanted} above {distractor} for {query}"
    assert cosine(surface.embed(query), surface.embed(wanted)) == pytest.approx(0.0, abs=1e-6)
