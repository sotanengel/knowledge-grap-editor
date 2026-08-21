"""Forward chaining with provenance (§10.1).

Materialisation, not query rewriting: derived triples are computed once, written
to ``urn:ontoforge:inferred``, and cost SPARQL nothing at query time.

The rule set is finite and monotonic -- every rule only ever adds triples, drawn
from terms already present -- so the process reaches a fixed point and stops. A
maximum iteration count and a derivation cap sit on top of that as a belt for
the braces.

Every derivation keeps the rule that made it and the premises it used, which is
what ``explain_inference`` reads back.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from pyoxigraph import BlankNode, Literal, NamedNode, Quad, Triple

from ontoforge.reasoning.rules import Pattern, Profile, Rule, rules_for

DEFAULT_MAX_ITERATIONS = 20
DEFAULT_MAX_DERIVATIONS = 1_000_000

Binding = dict[str, object]


@dataclass(frozen=True, slots=True)
class Derivation:
    """One derived triple and the reason it holds."""

    triple: Triple
    rule: str
    premises: tuple[Triple, ...]


@dataclass(slots=True)
class ReasoningResult:
    """What one materialisation run produced."""

    derivations: list[Derivation] = field(default_factory=list)
    iterations: int = 0
    reached_fixed_point: bool = True
    hit_derivation_cap: bool = False

    @property
    def count(self) -> int:
        return len(self.derivations)

    @property
    def triples(self) -> list[Triple]:
        return [derivation.triple for derivation in self.derivations]


def _match(pattern: Pattern, triple: Triple, binding: Binding) -> Binding | None:
    """Extend ``binding`` so ``pattern`` matches ``triple``, or fail."""
    extended = binding
    for slot, term in zip(pattern, (triple.subject, triple.predicate, triple.object), strict=True):
        if slot is None:
            continue
        if isinstance(slot, str):
            bound = extended.get(slot)
            if bound is None:
                if extended is binding:
                    extended = dict(binding)
                extended[slot] = term
            elif bound != term:
                return None
        elif slot != term:
            return None
    return extended


def _instantiate(pattern: Pattern, binding: Binding) -> Triple | None:
    """Build the conclusion triple, or ``None`` if it would not be well formed."""
    subject, predicate, obj = (binding[slot] if isinstance(slot, str) else slot for slot in pattern)
    if not isinstance(subject, NamedNode | Triple) or not isinstance(predicate, NamedNode):
        # A literal can never be a subject, nor anything but a NamedNode a
        # predicate; rules that would produce one simply do not fire.
        return None
    if not isinstance(obj, NamedNode | BlankNode | Literal | Triple):
        return None  # pragma: no cover - guarded by rule construction
    return Triple(subject, predicate, obj)


def _apply(rule: Rule, facts: Sequence[Triple]) -> Iterable[tuple[Triple, tuple[Triple, ...]]]:
    """Every conclusion ``rule`` draws from ``facts``, with the premises used."""
    frontier: list[tuple[Binding, tuple[Triple, ...]]] = [({}, ())]
    for pattern in rule.premises:
        extended: list[tuple[Binding, tuple[Triple, ...]]] = []
        for binding, used in frontier:
            for fact in facts:
                found = _match(pattern, fact, binding)
                if found is not None:
                    extended.append((found, (*used, fact)))
        frontier = extended
        if not frontier:
            return
    for binding, used in frontier:
        conclusion = _instantiate(rule.conclusion, binding)
        if conclusion is not None:
            yield conclusion, used


def materialise(
    asserted: Iterable[Quad | Triple],
    *,
    profile: Profile | str = Profile.RDFS,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    max_derivations: int = DEFAULT_MAX_DERIVATIONS,
) -> ReasoningResult:
    """Run the rules to a fixed point over ``asserted``."""
    rules = rules_for(profile)
    result = ReasoningResult()
    if not rules:
        return result

    base = {_as_triple(item) for item in asserted}
    known = set(base)
    derived: dict[Triple, Derivation] = {}

    for iteration in range(1, max_iterations + 1):
        result.iterations = iteration
        facts = sorted(known, key=str)
        fresh: list[Derivation] = []

        for rule in rules:
            for conclusion, premises in _apply(rule, facts):
                if conclusion in known:
                    continue
                known.add(conclusion)
                derivation = Derivation(triple=conclusion, rule=rule.name, premises=premises)
                derived[conclusion] = derivation
                fresh.append(derivation)
                if len(derived) >= max_derivations:
                    result.derivations = list(derived.values())
                    result.hit_derivation_cap = True
                    result.reached_fixed_point = False
                    return result

        if not fresh:
            result.derivations = list(derived.values())
            return result

    result.derivations = list(derived.values())
    result.reached_fixed_point = False
    return result


def explain(
    triple: Triple,
    asserted: Iterable[Quad | Triple],
    *,
    profile: Profile | str = Profile.RDFS,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> Derivation | None:
    """Why ``triple`` was derived, or ``None`` if the rules never produce it."""
    result = materialise(asserted, profile=profile, max_iterations=max_iterations)
    for derivation in result.derivations:
        if derivation.triple == triple:
            return derivation
    return None


def _as_triple(item: Quad | Triple) -> Triple:
    return item if isinstance(item, Triple) else Triple(item.subject, item.predicate, item.object)
