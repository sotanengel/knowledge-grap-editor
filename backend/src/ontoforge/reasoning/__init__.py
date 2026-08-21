"""Rule-based inference (§10.1, FR-11)."""

from ontoforge.reasoning.closure import entails, owl_closure
from ontoforge.reasoning.justify import CLOSURE_STEP, Justification, justify, name_step
from ontoforge.reasoning.noise import NoiseReason, is_noise, keep_signal
from ontoforge.reasoning.rules import Profile, Rule, describe_profile, rules_for
from ontoforge.reasoning.service import Explanation, ReasonerService, ReasonSummary

__all__ = [
    "CLOSURE_STEP",
    "Explanation",
    "Justification",
    "NoiseReason",
    "Profile",
    "ReasonSummary",
    "ReasonerService",
    "Rule",
    "describe_profile",
    "entails",
    "is_noise",
    "justify",
    "keep_signal",
    "name_step",
    "owl_closure",
    "rules_for",
]
