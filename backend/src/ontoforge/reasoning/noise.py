"""Deciding which derived triples are worth showing (§10.1, §7.3-4).

A complete OWL 2 RL closure is correct and mostly unreadable. Measured on a small
test ontology: 185 derived triples, of which 17 concerned the user's own data and
67 were ``x owl:sameAs x``. Drawing all of it as dashed edges would bury the
handful that matter.

So the closure stays complete and this decides what reaches the canvas. The two
are kept apart on purpose: what is *entailed* is a fact about the graph, what is
*worth showing* is a judgement, and only the second belongs here.

Nothing is deleted from the reasoning -- ``sparql_select`` and the closure still
see everything. This only governs what is written to ``urn:ontoforge:inferred``
and therefore what a person is shown.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import StrEnum
from typing import Literal

from pyoxigraph import NamedNode, Triple

from ontoforge.namespaces import OWL, RDF, RDF_TYPE, RDFS
from ontoforge.store.iri import SKOLEM_SUFFIX

#: Namespaces the reasoner will happily talk about, and which no user asked about.
META_NAMESPACES: tuple[str, ...] = (RDF, RDFS, OWL, "http://www.w3.org/2001/XMLSchema#")

#: Relating a thing to itself through one of these says nothing at all.
REFLEXIVE_PREDICATES: frozenset[NamedNode] = frozenset(
    {
        NamedNode(f"{OWL}sameAs"),
        NamedNode(f"{RDFS}subClassOf"),
        NamedNode(f"{RDFS}subPropertyOf"),
        NamedNode(f"{OWL}equivalentClass"),
        NamedNode(f"{OWL}equivalentProperty"),
    }
)

#: The classes everything belongs to, which is why saying so is not news.
UNIVERSAL_CLASSES: frozenset[NamedNode] = frozenset(
    {NamedNode(f"{OWL}Thing"), NamedNode(f"{RDFS}Resource")}
)

#: Predicates for which naming a universal class says nothing: everything is one,
#: everything is a subclass of one, and a domain or range of one constrains
#: nothing at all.
UNIVERSAL_PREDICATES: frozenset[NamedNode] = frozenset(
    {
        RDF_TYPE,
        NamedNode(f"{RDFS}subClassOf"),
        NamedNode(f"{RDFS}domain"),
        NamedNode(f"{RDFS}range"),
    }
)


class NoiseReason(StrEnum):
    """Why a derived triple was held back, so the answer is never just "hidden"."""

    TAUTOLOGY = "tautology"
    UNIVERSAL = "universal-class"
    VOCABULARY = "vocabulary-internal"
    CONSTRUCTION = "class-construction"

    @property
    def explanation(self) -> str:
        return _EXPLANATIONS[self]


_EXPLANATIONS: dict[NoiseReason, str] = {
    NoiseReason.TAUTOLOGY: "それ自身との関係で、何も述べていないため",
    NoiseReason.UNIVERSAL: "すべてのものが属するクラスで、区別にならないため",
    NoiseReason.VOCABULARY: "RDF / OWL 語彙自身についての導出で、利用者のデータではないため",
    NoiseReason.CONSTRUCTION: "クラス定義の内部構造で、事実そのものではないため",
}


def noise_reason(
    triple: Triple,
    *,
    base_iri: str,
    vocabulary_namespaces: Sequence[str] = (),
) -> NoiseReason | None:
    """Why ``triple`` should stay off the canvas, or ``None`` if it should not."""
    subject, predicate, obj = triple.subject, triple.predicate, triple.object

    if predicate in REFLEXIVE_PREDICATES and subject == obj:
        return NoiseReason.TAUTOLOGY

    if predicate in UNIVERSAL_PREDICATES and obj in UNIVERSAL_CLASSES:
        return NoiseReason.UNIVERSAL

    skolem = f"{base_iri}{SKOLEM_SUFFIX}"
    if _starts_with(subject, skolem) or _starts_with(obj, skolem):
        # Restriction and list nodes, skolemised on the way in (§4.3). They are
        # how a class definition is built, not something anyone asserted.
        return NoiseReason.CONSTRUCTION

    excluded = (*META_NAMESPACES, *vocabulary_namespaces)
    if _starts_with(subject, *excluded):
        return NoiseReason.VOCABULARY

    return None


def is_noise(
    triple: Triple,
    *,
    base_iri: str,
    vocabulary_namespaces: Sequence[str] = (),
) -> bool:
    return (
        noise_reason(triple, base_iri=base_iri, vocabulary_namespaces=vocabulary_namespaces)
        is not None
    )


def keep_signal(
    derived: Iterable[Triple],
    *,
    base_iri: str,
    vocabulary_namespaces: Sequence[str] = (),
) -> tuple[set[Triple], dict[NoiseReason, int]]:
    """Split a closure into what to show and a tally of what was held back."""
    kept: set[Triple] = set()
    removed: dict[NoiseReason, int] = dict.fromkeys(NoiseReason, 0)

    for triple in derived:
        reason = noise_reason(
            triple, base_iri=base_iri, vocabulary_namespaces=vocabulary_namespaces
        )
        if reason is None:
            kept.add(triple)
        else:
            removed[reason] += 1
    return kept, removed


def summarise_removed(removed: dict[NoiseReason, int]) -> list[dict[str, object]]:
    """The tally in the shape the settings screen can render."""
    return [
        {"reason": reason.value, "count": count, "explanation": reason.explanation}
        for reason, count in removed.items()
        if count
    ]


def _starts_with(term: object, *prefixes: str) -> bool:
    if not isinstance(term, NamedNode):
        return False
    return any(term.value.startswith(prefix) for prefix in prefixes)


PremiseKind = Literal["fact", "definition"]


def is_construction(term: object, *, base_iri: str) -> bool:
    """Whether ``term`` is a skolemised restriction or list node (§4.3)."""
    if not base_iri or not isinstance(term, NamedNode):
        return False
    return term.value.startswith(f"{base_iri}{SKOLEM_SUFFIX}")


def premise_kind(triple: Triple, *, base_iri: str) -> PremiseKind:
    """Whether a premise states something, or shapes the vocabulary.

    A justification mixes the two. "田中太郎 worksFor アクメ東京" is a fact somebody
    entered; ``ont:worksFor owl:propertyChainAxiom ( … )`` and the RDF list nodes
    it is written as are how an axiom is spelled. Both belong in the answer --
    the conclusion does not follow without either -- but presenting them as the
    same kind of thing is what made an explanation hard to read.
    """
    if is_construction(triple.subject, base_iri=base_iri) or is_construction(
        triple.object, base_iri=base_iri
    ):
        return "definition"

    if triple.predicate == RDF_TYPE:
        # "alice a Person" says something about Alice; "Person a owl:Class" is
        # part of setting the vocabulary up.
        return "definition" if _starts_with(triple.object, *META_NAMESPACES) else "fact"

    return "definition" if _starts_with(triple.predicate, *META_NAMESPACES) else "fact"
