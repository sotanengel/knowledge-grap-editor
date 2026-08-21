"""Working out why a triple was derived, when the reasoner will not say (§10.1).

§10.1 asks that every derived triple keep "the rule that produced it and the
premises it used". owlrl produces the closure and keeps neither.

So the reason is recovered afterwards, from the outside: take the facts that
could plausibly be involved, and shrink that set for as long as the conclusion
still follows. What is left is a *justification* -- a minimal set of asserted
facts that entails the conclusion. Every premise in it is load-bearing, because
anything that could be dropped was.

The shrinking is QuickXplain's divide-and-conquer rather than dropping one fact
at a time, which matters because each test runs a full closure: over ~75
candidates that is roughly 30 closure runs instead of 75.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from pyoxigraph import Triple

from ontoforge.reasoning.engine import _apply
from ontoforge.reasoning.rules import Profile, rules_for

#: What the step is called when no rule this project can execute accounts for it.
CLOSURE_STEP = "OWL 2 RL closure"

#: Below this, splitting costs more than it saves.
_SPLIT_THRESHOLD = 4

Entails = Callable[[Sequence[Triple], Triple], bool]


@dataclass(frozen=True, slots=True)
class Justification:
    """A minimal set of asserted facts that entails a derived one."""

    conclusion: Triple
    premises: list[Triple] = field(default_factory=list)
    rule: str = CLOSURE_STEP

    @property
    def is_direct(self) -> bool:
        """Whether the conclusion was simply asserted rather than derived."""
        return self.premises == [self.conclusion]


def justify(
    conclusion: Triple,
    candidates: Sequence[Triple],
    entails: Entails,
    *,
    profile: Profile = Profile.OWL2_RL,
) -> Justification | None:
    """The smallest subset of ``candidates`` that still entails ``conclusion``.

    Where a conclusion can be reached by more than one route -- "Alice is a
    Person" both because she is an Employee and because ``worksFor`` has Person
    as its domain -- one of them comes back, not all of them. Each is a complete
    answer to "why does this hold"; enumerating every route is a different and
    much more expensive question.

    ``None`` when the candidates do not entail it at all, which is the honest
    answer when the reason lies outside the neighbourhood that was searched.
    """
    pool = list(candidates)
    if not pool or not entails(pool, conclusion):
        return None

    minimal = _shrink(pool, [], conclusion, entails)
    return Justification(
        conclusion=conclusion,
        premises=minimal,
        rule=name_step(conclusion, minimal, profile=profile),
    )


def _shrink(
    candidates: list[Triple],
    kept: list[Triple],
    conclusion: Triple,
    entails: Entails,
) -> list[Triple]:
    """QuickXplain: halve the candidates while the conclusion still follows."""
    if kept and entails(kept, conclusion):
        return []
    if len(candidates) == 1:
        return candidates
    if len(candidates) <= _SPLIT_THRESHOLD:
        return _drop_one_at_a_time(candidates, kept, conclusion, entails)

    middle = len(candidates) // 2
    left, right = candidates[:middle], candidates[middle:]

    from_right = _shrink(right, [*kept, *left], conclusion, entails)
    from_left = _shrink(left, [*kept, *from_right], conclusion, entails)
    return [*from_left, *from_right]


def _drop_one_at_a_time(
    candidates: list[Triple],
    kept: list[Triple],
    conclusion: Triple,
    entails: Entails,
) -> list[Triple]:
    """The base case, where splitting no longer pays for itself."""
    remaining = list(candidates)
    for triple in list(remaining):
        trial = [item for item in remaining if item != triple]
        if entails([*kept, *trial], conclusion):
            remaining = trial
    return remaining


def name_step(
    conclusion: Triple,
    premises: Sequence[Triple],
    *,
    profile: Profile = Profile.OWL2_RL,
) -> str:
    """Which rule accounts for this step in one move, if any of ours does.

    owlrl covers a good deal more than the rules this project can execute, so a
    great many justifications have no name here. Those say so rather than being
    attributed to a rule that never ran.
    """
    if list(premises) == [conclusion]:
        return "asserted"

    facts = list(premises)
    for rule in rules_for(profile):
        for derived, _used in _apply(rule, facts):
            if derived == conclusion:
                return rule.name
    return CLOSURE_STEP
