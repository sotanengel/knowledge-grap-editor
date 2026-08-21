"""Running the reasoner against the store (§10.1, FR-11).

The closure comes from owlrl (§5.3). What reaches ``urn:ontoforge:inferred`` is
that closure minus the part nobody wants to look at -- see
:mod:`ontoforge.reasoning.noise` for what "nobody wants to look at" means and
why the decision lives apart from the reasoning itself.

Two things go into the graph for each surviving derivation:

* **the derived triple itself**, so SPARQL can query it. That is the whole
  reason §10.1 chose materialisation over query rewriting;
* **a marker** saying it was derived rather than asserted, which is what lets
  the canvas draw it dashed and refuse to let anyone edit it.

The *reason* is not stored. owlrl does not produce one, and recovering it costs
a search (:mod:`ontoforge.reasoning.justify`), so it is worked out when someone
asks and cached in memory. That also means the read-only MCP handle can answer
``explain_inference`` without needing anything written for it in advance.

The whole graph is regenerable, so it is rewritten wholesale and recorded under
the ``reasoner`` actor rather than piled into the user's undo history.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from pyoxigraph import Literal, NamedNode, Quad, Triple

from ontoforge.literals import XSD_STRING
from ontoforge.namespaces import ONTF, RDF_REIFIES
from ontoforge.reasoning.closure import entails as closure_entails
from ontoforge.reasoning.closure import owl_closure
from ontoforge.reasoning.justify import CLOSURE_STEP, justify
from ontoforge.reasoning.noise import (
    NoiseReason,
    is_construction,
    keep_signal,
    premise_kind,
    summarise_removed,
)
from ontoforge.reasoning.rules import Profile
from ontoforge.runtime import Runtime
from ontoforge.store import graphs

DERIVATION_PREFIX = "derivation/"
ACTOR = "reasoner"

#: The graph records which profile produced it, so an explanation is worked out
#: under the same rules that derived the triple -- not under whatever the
#: configured default happens to be now. It also survives a restart, which is
#: what lets the read-only MCP handle explain anything at all.
RUN_MARKER = NamedNode("urn:ontoforge:inferred")
ONTF_PROFILE = NamedNode(f"{ONTF}profile")

#: How many neighbourhood triples an explanation will search. Beyond this the
#: search costs more than the answer is worth, and it says so instead.
MAX_EXPLANATION_CANDIDATES = 400
#: How many answers to remember. Explanations are asked for one at a time, by
#: hand, so a small cache covers the realistic pattern of use.
EXPLANATION_CACHE_SIZE = 256


@dataclass(frozen=True, slots=True)
class ReasonSummary:
    """What ``POST /reason`` reports back."""

    profile: str
    derived: int
    suppressed: int
    suppressed_by_reason: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Explanation:
    """The answer to "why is this here?"."""

    triple: dict[str, str]
    rule: str
    premises: list[dict[str, str]]
    note: str = ""


class ReasonerService:
    """Materialises the inferred graph and works out why each entry is there."""

    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime
        self._explanations: OrderedDict[Triple, Explanation | None] = OrderedDict()

    @property
    def profile(self) -> Profile:
        return Profile(self.runtime.settings.reasoner)

    # ------------------------------------------------------------------ run

    def run(self, *, profile: Profile | str | None = None) -> ReasonSummary:
        """Rebuild ``urn:ontoforge:inferred`` from scratch."""
        chosen = Profile(profile) if profile is not None else self.profile
        asserted = self._asserted()

        closure = owl_closure(asserted, profile=chosen)
        kept, removed = keep_signal(
            closure,
            base_iri=self.runtime.settings.base_iri,
            vocabulary_namespaces=self._vocabulary_namespaces(),
        )
        self._replace_inferred(kept, profile=chosen)
        self._explanations.clear()

        return ReasonSummary(
            profile=chosen.value,
            derived=len(kept),
            suppressed=sum(removed.values()),
            suppressed_by_reason=summarise_removed(removed),
        )

    def clear(self) -> None:
        self._replace_inferred(set(), profile=Profile.NONE)
        self._explanations.clear()

    @property
    def last_profile(self) -> Profile:
        """The profile that produced the graph as it stands.

        An explanation has to be worked out under the rules that actually
        derived the triple; the configured default may have moved on since.
        """
        for quad in self.runtime.store.quads_for_pattern(
            RUN_MARKER, ONTF_PROFILE, None, graphs.INFERRED
        ):
            if isinstance(quad.object, Literal):
                try:
                    return Profile(quad.object.value)
                except ValueError:  # pragma: no cover - a hand-edited graph
                    break
        return self.profile

    def _asserted(self) -> list[Quad]:
        """What the reasoner sees: the user's own graphs plus any loaded vocabulary."""
        sources = [
            graphs.ONTOLOGY,
            graphs.DATA,
            *[graph for graph in self.runtime.store.named_graphs() if graphs.is_vocab_graph(graph)],
        ]
        return [
            quad
            for graph in sources
            for quad in self.runtime.store.quads_for_pattern(None, None, None, graph)
        ]

    def _vocabulary_namespaces(self) -> list[str]:
        """Namespaces of the loaded vocabularies, so the reasoner's remarks about
        them stay out of the user's view."""
        from ontoforge.vocab import loader

        loaded = set(loader.loaded_names(self.runtime.store))
        return [vocabulary.namespace for vocabulary in loader.BUNDLED if vocabulary.name in loaded]

    def _replace_inferred(self, derived: set[Triple], *, profile: Profile) -> None:
        existing = list(self.runtime.store.quads_for_pattern(None, None, None, graphs.INFERRED))
        additions: list[Quad] = []
        if derived:
            # Only worth recording when there is something to explain; an empty
            # inferred graph should be genuinely empty.
            additions.append(
                Quad(
                    RUN_MARKER,
                    ONTF_PROFILE,
                    Literal(profile.value, datatype=XSD_STRING),
                    graphs.INFERRED,
                )
            )
        for triple in derived:
            # The triple itself, so `GRAPH <urn:ontoforge:inferred> { ... }` works.
            additions.append(Quad(triple.subject, triple.predicate, triple.object, graphs.INFERRED))
            # And a marker, so the canvas can tell it apart from what was typed.
            additions.append(Quad(_record_node(triple), RDF_REIFIES, triple, graphs.INFERRED))
        self.runtime.write(additions=additions, deletions=existing, actor=ACTOR)

    # ------------------------------------------------------------------ read

    def derived_triples(self) -> list[Triple]:
        """The inferred triples, read from their markers."""
        return [
            quad.object
            for quad in self.runtime.store.quads_for_pattern(
                None, RDF_REIFIES, None, graphs.INFERRED
            )
            if isinstance(quad.object, Triple)
        ]

    def is_derived(self, triple: Triple) -> bool:
        return any(self.runtime.store.quads_for_pattern(None, RDF_REIFIES, triple, graphs.INFERRED))

    def explain(self, triple: Triple) -> Explanation | None:
        """Why a derived triple holds (§10.1, ``explain_inference``).

        ``None`` when the triple was not derived at all -- it was either asserted
        outright or is not in the graph.
        """
        if triple in self._explanations:
            self._explanations.move_to_end(triple)
            return self._explanations[triple]

        found = self._explain_uncached(triple)
        self._explanations[triple] = found
        while len(self._explanations) > EXPLANATION_CACHE_SIZE:
            self._explanations.popitem(last=False)
        return found

    def _explain_uncached(self, triple: Triple) -> Explanation | None:
        if not self.is_derived(triple):
            return None

        base = self.runtime.settings.base_iri
        candidates = self._candidates(triple)
        if len(candidates) > MAX_EXPLANATION_CANDIDATES:
            return Explanation(
                triple=_triple_json(triple, base_iri=base),
                rule=CLOSURE_STEP,
                premises=[],
                note=(
                    f"根拠の候補が {len(candidates)} 件あり、探索を打ち切りました。"
                    "オントロジーを小さくするか、対象を絞ってからお試しください。"
                ),
            )

        profile = self.last_profile

        def entails(premises: Any, conclusion: Triple) -> bool:
            return closure_entails(premises, conclusion, profile=profile)

        found = justify(triple, candidates, entails, profile=profile)
        if found is None:
            return Explanation(
                triple=_triple_json(triple, base_iri=base),
                rule=CLOSURE_STEP,
                premises=[],
                note=(
                    "近傍とオントロジーの範囲では根拠を特定できませんでした。"
                    "離れた場所の記述が関わっている可能性があります。"
                ),
            )

        return Explanation(
            triple=_triple_json(triple, base_iri=base),
            rule=found.rule,
            premises=[_triple_json(premise, base_iri=base) for premise in found.premises],
            note="" if found.rule != CLOSURE_STEP else "OWL 2 RL の閉包規則によるものです。",
        )

    def _candidates(self, triple: Triple) -> list[Triple]:
        """What could plausibly account for ``triple``.

        The neighbourhood of both ends, what is said about the predicates
        involved, and the whole ontology. Loaded vocabularies are left out on
        purpose: schema.org alone is 18,000 triples, and searching it would make
        the answer arrive far too late to be useful.
        """
        found: dict[Triple, None] = {}

        for graph in (graphs.ONTOLOGY,):
            for quad in self.runtime.store.quads_for_pattern(None, None, None, graph):
                found[Triple(quad.subject, quad.predicate, quad.object)] = None

        for end in (triple.subject, triple.object):
            if not isinstance(end, NamedNode):
                continue
            for quad in self.runtime.store.describe(end, depth=2, search=[graphs.DATA]):
                found[Triple(quad.subject, quad.predicate, quad.object)] = None
            for quad in self.runtime.store.quads_for_pattern(None, None, end, graphs.DATA):
                found[Triple(quad.subject, quad.predicate, quad.object)] = None

        self._add_property_axioms(triple, found)
        return list(found)

    def _add_property_axioms(self, triple: Triple, found: dict[Triple, None]) -> None:
        """What is said about the properties in play -- which is often the reason.

        ``rdfs:domain``, ``owl:propertyChainAxiom``, ``owl:TransitiveProperty``
        and their kin hang off the *predicate*, so a search that gathers only the
        subject and object of the conclusion cannot see them. A chain axiom in
        particular mentions neither end, which left every chained conclusion
        reported as an unexplained closure step.

        Predicates are few even in a large graph, and the depth follows the RDF
        list a chain axiom is written as, so this stays cheap.
        """
        properties = {triple.predicate} | {
            candidate.predicate for candidate in found if isinstance(candidate.predicate, NamedNode)
        }
        for prop in properties:
            for quad in self.runtime.store.describe(prop, depth=3, search=[graphs.DATA]):
                found[Triple(quad.subject, quad.predicate, quad.object)] = None


def _record_node(triple: Triple) -> NamedNode:
    """A stable name for the marker, so re-running does not churn the graph."""
    digest = hashlib.sha256(str(triple).encode("utf-8")).hexdigest()[:26]
    return NamedNode(f"urn:ontoforge:{DERIVATION_PREFIX}{digest}")


#: How a skolemised node reads once it is no longer an opaque identifier.
ANONYMOUS = "（定義）"


def _triple_json(triple: Triple, *, base_iri: str = "") -> dict[str, str]:
    """One triple in the shape the API and the MCP tool return.

    ``kind`` separates what someone asserted from the structure of a definition;
    :func:`~ontoforge.reasoning.noise.premise_kind` decides which, so the REST
    answer and the MCP answer never disagree about it.
    """
    from ontoforge.io.graphview import local_name

    def readable(term: object) -> str:
        # ``str`` on a node wraps it in angle brackets, which then survive the
        # split and leave a stray ">" on every name. The value is the IRI itself.
        value = getattr(term, "value", None)
        if not isinstance(value, str):
            return str(term)
        if is_construction(term, base_iri=base_iri):
            return ANONYMOUS
        return local_name(value)

    return {
        "subject": str(triple.subject),
        "predicate": str(triple.predicate),
        "object": str(triple.object),
        "kind": premise_kind(triple, base_iri=base_iri),
        "text": (
            f"{readable(triple.subject)} {readable(triple.predicate)} {readable(triple.object)}"
        ),
    }


__all__ = ["Explanation", "NoiseReason", "ReasonSummary", "ReasonerService"]
