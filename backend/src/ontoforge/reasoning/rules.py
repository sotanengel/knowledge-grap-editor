"""The inference rules, and nothing beyond them (§10.1).

The deliberate limit is "what can be reached by applying rules forwards until
nothing new appears". No satisfiability checking, no class-expression
classification, no cardinality contradiction hunting -- those need a description
logic reasoner, another container and a long batch, and SHACL covers the checks
people actually want (§10.2).

Every rule names itself, so each derived triple can say which rule produced it
and from what. That is what makes ``explain_inference`` possible.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from pyoxigraph import NamedNode

from ontoforge.namespaces import OWL, RDF_TYPE, RDFS_SUBCLASS_OF, RDFS_SUBPROPERTY_OF
from ontoforge.namespaces import RDFS_DOMAIN as DOMAIN
from ontoforge.namespaces import RDFS_RANGE as RANGE

OWL_INVERSE_OF = NamedNode(f"{OWL}inverseOf")
OWL_TRANSITIVE_PROPERTY = NamedNode(f"{OWL}TransitiveProperty")
OWL_SYMMETRIC_PROPERTY = NamedNode(f"{OWL}SymmetricProperty")
OWL_EQUIVALENT_CLASS = NamedNode(f"{OWL}equivalentClass")
OWL_EQUIVALENT_PROPERTY = NamedNode(f"{OWL}equivalentProperty")
OWL_SAME_AS = NamedNode(f"{OWL}sameAs")


class Profile(StrEnum):
    """How much inference to do (§10.1, ``ONTOFORGE_REASONER``)."""

    NONE = "none"
    RDFS = "rdfs"
    RL_LITE = "rl-lite"


#: A pattern is a triple of terms, where ``None`` in a slot matches anything and
#: a plain string is a variable that must bind consistently across the rule.
Term = NamedNode | str | None
Pattern = tuple[Term, Term, Term]


@dataclass(frozen=True, slots=True)
class Rule:
    """One forward-chaining rule: match every premise, assert the conclusion."""

    name: str
    premises: tuple[Pattern, ...]
    conclusion: Pattern
    description: str

    def variables(self) -> set[str]:
        return {
            term
            for pattern in (*self.premises, self.conclusion)
            for term in pattern
            if isinstance(term, str)
        }


RDFS_RULES: tuple[Rule, ...] = (
    Rule(
        name="rdfs:subClassOf-transitive",
        premises=(("a", RDFS_SUBCLASS_OF, "b"), ("b", RDFS_SUBCLASS_OF, "c")),
        conclusion=("a", RDFS_SUBCLASS_OF, "c"),
        description="サブクラスの推移閉包",
    ),
    Rule(
        name="rdfs:subClassOf-type",
        premises=(("x", RDF_TYPE, "a"), ("a", RDFS_SUBCLASS_OF, "b")),
        conclusion=("x", RDF_TYPE, "b"),
        description="親クラスの型を継承する（社員は人物でもある）",
    ),
    Rule(
        name="rdfs:subPropertyOf-transitive",
        premises=(("p", RDFS_SUBPROPERTY_OF, "q"), ("q", RDFS_SUBPROPERTY_OF, "r")),
        conclusion=("p", RDFS_SUBPROPERTY_OF, "r"),
        description="サブプロパティの推移閉包",
    ),
    Rule(
        name="rdfs:subPropertyOf-assert",
        premises=(("x", "p", "y"), ("p", RDFS_SUBPROPERTY_OF, "q")),
        conclusion=("x", "q", "y"),
        description="親プロパティでも成り立つ",
    ),
    Rule(
        name="rdfs:domain",
        premises=(("p", DOMAIN, "c"), ("x", "p", "y")),
        conclusion=("x", RDF_TYPE, "c"),
        description="定義域から主語の型を導く",
    ),
    Rule(
        name="rdfs:range",
        premises=(("p", RANGE, "c"), ("x", "p", "y")),
        conclusion=("y", RDF_TYPE, "c"),
        description="値域から目的語の型を導く",
    ),
)

RL_LITE_RULES: tuple[Rule, ...] = (
    Rule(
        name="owl:inverseOf",
        premises=(("p", OWL_INVERSE_OF, "q"), ("x", "p", "y")),
        conclusion=("y", "q", "x"),
        description="逆向きの関係を埋める（所属 ⇄ 所属員）",
    ),
    Rule(
        name="owl:inverseOf-reverse",
        premises=(("p", OWL_INVERSE_OF, "q"), ("y", "q", "x")),
        conclusion=("x", "p", "y"),
        description="逆向きの関係を埋める（反対方向）",
    ),
    Rule(
        name="owl:TransitiveProperty",
        premises=(("p", RDF_TYPE, OWL_TRANSITIVE_PROPERTY), ("x", "p", "y"), ("y", "p", "z")),
        conclusion=("x", "p", "z"),
        description="推移的な関係をたどる（部分の部分は部分）",
    ),
    Rule(
        name="owl:SymmetricProperty",
        premises=(("p", RDF_TYPE, OWL_SYMMETRIC_PROPERTY), ("x", "p", "y")),
        conclusion=("y", "p", "x"),
        description="対称な関係は両向きに成り立つ",
    ),
    Rule(
        name="owl:equivalentClass-forward",
        premises=(("a", OWL_EQUIVALENT_CLASS, "b"),),
        conclusion=("a", RDFS_SUBCLASS_OF, "b"),
        description="同値クラスは互いのサブクラス",
    ),
    Rule(
        name="owl:equivalentClass-backward",
        premises=(("a", OWL_EQUIVALENT_CLASS, "b"),),
        conclusion=("b", RDFS_SUBCLASS_OF, "a"),
        description="同値クラスは互いのサブクラス（反対方向）",
    ),
    Rule(
        name="owl:equivalentProperty-forward",
        premises=(("p", OWL_EQUIVALENT_PROPERTY, "q"),),
        conclusion=("p", RDFS_SUBPROPERTY_OF, "q"),
        description="同値プロパティは互いのサブプロパティ",
    ),
    Rule(
        name="owl:equivalentProperty-backward",
        premises=(("p", OWL_EQUIVALENT_PROPERTY, "q"),),
        conclusion=("q", RDFS_SUBPROPERTY_OF, "p"),
        description="同値プロパティは互いのサブプロパティ（反対方向）",
    ),
    Rule(
        name="owl:sameAs-symmetric",
        premises=(("x", OWL_SAME_AS, "y"),),
        conclusion=("y", OWL_SAME_AS, "x"),
        description="同一性は対称",
    ),
    Rule(
        name="owl:sameAs-subject",
        premises=(("x", OWL_SAME_AS, "y"), ("x", "p", "o")),
        conclusion=("y", "p", "o"),
        description="同一のものが主語なら同じことが言える",
    ),
    Rule(
        name="owl:sameAs-object",
        premises=(("x", OWL_SAME_AS, "y"), ("s", "p", "x")),
        conclusion=("s", "p", "y"),
        description="同一のものが目的語なら同じことが言える",
    ),
)

_BY_PROFILE: dict[Profile, tuple[Rule, ...]] = {
    Profile.NONE: (),
    Profile.RDFS: RDFS_RULES,
    Profile.RL_LITE: RDFS_RULES + RL_LITE_RULES,
}


def rules_for(profile: Profile | str) -> Sequence[Rule]:
    """The rule set a profile applies."""
    return _BY_PROFILE[Profile(profile)]


def describe_profile(profile: Profile | str) -> list[dict[str, str]]:
    """Rule names and plain-language descriptions, for the settings screen."""
    return [{"name": rule.name, "description": rule.description} for rule in rules_for(profile)]
