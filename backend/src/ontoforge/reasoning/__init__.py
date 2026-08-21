"""Rule-based inference (§10.1, FR-11)."""

from ontoforge.reasoning.engine import Derivation, ReasoningResult, explain, materialise
from ontoforge.reasoning.rules import Profile, Rule, describe_profile, rules_for
from ontoforge.reasoning.service import Explanation, ReasonerService, ReasonSummary

__all__ = [
    "Derivation",
    "Explanation",
    "Profile",
    "ReasonSummary",
    "ReasonerService",
    "ReasoningResult",
    "Rule",
    "describe_profile",
    "explain",
    "materialise",
    "rules_for",
]
