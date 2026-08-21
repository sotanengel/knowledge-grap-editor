"""Turning a label into a vector -- and being clear about which kind (§14 Phase 3).

Two implementations, one interface, and the difference between them is stated
rather than hidden:

* :class:`StaticEmbedder` is a real embedding. It carries the distilled weights
  of a trained multilingual sentence model (model2vec ``potion-multilingual-128M``,
  quantised to int8 and truncated to 128 dimensions), so 「会社」 and 「企業」 come
  out close although they share no character.
* :class:`HashingEmbedder` is not. It hashes character n-grams, so it finds
  「田中太郎」 from 「田中」 and nothing at all from 「企業」.

The second exists because the first is fetched at build time and a source
checkout has no model. Rather than failing, the tool falls back -- and every
surface that reports a similarity says which one produced it, so nobody reads
more into a score than is there.

Inference for the static model is a lookup, a mean and a normalise; that is all
model2vec does at run time. Doing it here keeps the runtime dependencies to
numpy and tokenizers, and keeps the behaviour identical on amd64 and arm64.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

#: Files a usable model directory must contain.
MODEL_FILES = ("embeddings.i8.npy", "meta.json", "tokenizer.json")

#: Fallback vector width. Wide enough that hash collisions stay rare.
HASHING_DIMENSIONS = 512
#: Character n-gram sizes; 2 and 3 together suit CJK and latin alike.
NGRAM_SIZES = (2, 3)

Quality = Literal["semantic", "surface"]

_WHITESPACE = re.compile(r"\s+")

FALLBACK_NOTE = (
    "ラベルの文字 n-gram による類似度です。学習済み埋め込みではないため、"
    "表記のゆれや部分一致には効きますが、意味の近さは捉えません。"
)
SEMANTIC_NOTE = (
    "多言語の学習済み埋め込み（model2vec potion-multilingual-128M を int8・128 次元へ"
    "圧縮）による類似度です。文字が重ならなくても意味が近ければ見つかります。"
)


@runtime_checkable
class Embedder(Protocol):
    """What every embedder has to offer, including an honest self-description."""

    name: str
    dimensions: int
    quality: Quality
    note: str

    def embed(self, text: str) -> list[float]: ...


def normalise(text: str) -> str:
    """Fold width and case so ＡＢＣ, ABC and abc are treated alike."""
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", text).casefold()).strip()


def cosine(left: list[float], right: list[float]) -> float:
    """Both vectors are unit length, so the dot product is the cosine."""
    return sum(a * b for a, b in zip(left, right, strict=True))


def _unit(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(value * value for value in vector))
    if length == 0.0:
        return vector
    return [value / length for value in vector]


# ---------------------------------------------------------------------- fallback


def ngrams(text: str, sizes: tuple[int, ...] = NGRAM_SIZES) -> list[str]:
    cleaned = normalise(text)
    if not cleaned:
        return []
    found: list[str] = []
    for size in sizes:
        if len(cleaned) < size:
            found.append(cleaned)
            continue
        found.extend(cleaned[index : index + size] for index in range(len(cleaned) - size + 1))
    return found


def _stable_hash(text: str) -> int:
    """Python's ``hash`` is salted per process; an index outlives the process."""
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "big")


class HashingEmbedder:
    """Surface similarity from hashed character n-grams.

    Good at what it is good at -- spelling variants, partial names, near-duplicate
    labels -- and no good at all at meaning. It says so.
    """

    quality: Quality = "surface"
    note = FALLBACK_NOTE

    def __init__(self, *, dimensions: int = HASHING_DIMENSIONS) -> None:
        self.dimensions = dimensions
        self.name = f"character-ngram ({dimensions}d)"

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for gram in ngrams(text):
            vector[_stable_hash(gram) % self.dimensions] += 1.0
        return _unit(vector)


# ---------------------------------------------------------------------- the model


class StaticEmbedder:
    """A trained embedding, carried as a quantised lookup table.

    model2vec's inference is a token lookup, a mean and a normalise, so no
    inference runtime is needed -- which is also why it behaves identically on
    every architecture the image is built for (NFR-01).
    """

    quality: Quality = "semantic"
    note = SEMANTIC_NOTE

    def __init__(self, directory: Path | str) -> None:
        import numpy as np
        from tokenizers import Tokenizer

        self.directory = Path(directory)
        if not model_is_available(self.directory):
            raise FileNotFoundError(f"no embedding model at {self.directory}")

        meta = json.loads((self.directory / "meta.json").read_text(encoding="utf-8"))
        self._matrix = np.load(self.directory / "embeddings.i8.npy")
        self._scale = float(meta["scale"])
        self._tokenizer = Tokenizer.from_file(str(self.directory / "tokenizer.json"))
        self.dimensions = int(meta["dimensions"])
        self.name = str(meta.get("name", "potion-multilingual-128M"))

    def embed(self, text: str) -> list[float]:
        import numpy as np

        cleaned = normalise(text)
        if not cleaned:
            return [0.0] * self.dimensions

        ids = self._tokenizer.encode(cleaned, add_special_tokens=False).ids
        if not ids:
            return [0.0] * self.dimensions

        rows = self._matrix[ids].astype(np.float32).mean(axis=0) * self._scale
        length = float(np.linalg.norm(rows))
        if length == 0.0:
            return [0.0] * self.dimensions
        return [float(value) for value in rows / length]


# ---------------------------------------------------------------------- choosing


def model_is_available(directory: Path | str) -> bool:
    """Whether ``directory`` holds a complete model, not a half-written one."""
    path = Path(directory)
    return all((path / name).is_file() for name in MODEL_FILES)


def default_model_dir() -> Path:
    """Where the build stage puts the model."""
    return Path(__file__).resolve().parent / "model"


def load_embedder(directory: Path | str | None = None) -> Embedder:
    """The real model where it was built in, the fallback otherwise.

    A missing model is a normal state -- a source checkout has none -- so this
    never raises. What it must not do is pretend, which is why the embedder it
    returns always carries its own ``quality`` and ``note``.
    """
    path = Path(directory) if directory is not None else default_model_dir()
    if not model_is_available(path):
        return HashingEmbedder()
    try:
        return StaticEmbedder(path)
    except (ImportError, OSError, ValueError, KeyError):
        # A model that cannot be loaded is worse than no model, because it would
        # fail every request. Falling back keeps search working and says so.
        return HashingEmbedder()


def describe(embedder: Embedder) -> dict[str, object]:
    """What the API and the interface report about the embedder in use."""
    return {
        "embedder": embedder.name,
        "quality": embedder.quality,
        "dimensions": embedder.dimensions,
        "note": embedder.note,
    }
