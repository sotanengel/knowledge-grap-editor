"""Optional similar-label search (§14 Phase 3). Off unless switched on."""

from ontoforge.semantic.embedder import (
    Embedder,
    HashingEmbedder,
    StaticEmbedder,
    cosine,
    default_model_dir,
    describe,
    load_embedder,
    model_is_available,
)
from ontoforge.semantic.vectors import Similar, VectorIndex

__all__ = [
    "Embedder",
    "HashingEmbedder",
    "Similar",
    "StaticEmbedder",
    "VectorIndex",
    "cosine",
    "default_model_dir",
    "describe",
    "load_embedder",
    "model_is_available",
]
