"""Optional local vector search (§14 Phase 3). Off unless switched on."""

from ontoforge.semantic.vectors import DIMENSIONS, Similar, VectorIndex, cosine, embed

__all__ = ["DIMENSIONS", "Similar", "VectorIndex", "cosine", "embed"]
