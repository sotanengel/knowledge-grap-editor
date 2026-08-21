"""SHACL constraints and validation (§10.2, FR-10)."""

from ontoforge.validation.service import Finding, ValidationReport, ValidationService
from ontoforge.validation.shapes import PropertyConstraint, ShapeSpec

__all__ = [
    "Finding",
    "PropertyConstraint",
    "ShapeSpec",
    "ValidationReport",
    "ValidationService",
]
