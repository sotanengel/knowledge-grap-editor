"""Running the reasoner against the store (§10.1, FR-11).

Derived triples go into ``urn:ontoforge:inferred`` alongside a provenance record
per triple, written with the same RDF 1.2 reifier machinery the edge metadata
uses. Keeping the record in the graph rather than in memory means the MCP server
can answer ``explain_inference`` from a read-only handle, with no shared state
and no second run of the rules.

The whole graph is regenerable, so it is rewritten wholesale and recorded with
the ``reasoner`` actor rather than piled into the user's undo history.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyoxigraph import Literal, NamedNode, Quad, Triple

from ontoforge.literals import XSD_STRING
from ontoforge.namespaces import ONTF, RDF_REIFIES
from ontoforge.reasoning.engine import Derivation, ReasoningResult, materialise
from ontoforge.reasoning.rules import Profile
from ontoforge.runtime import Runtime
from ontoforge.store import graphs

ONTF_RULE = NamedNode(f"{ONTF}rule")
ONTF_PREMISE = NamedNode(f"{ONTF}premise")
DERIVATION_PREFIX = "derivation/"

ACTOR = "reasoner"


@dataclass(frozen=True, slots=True)
class ReasonSummary:
    """What ``POST /reason`` reports back."""

    profile: str
    derived: int
    iterations: int
    reached_fixed_point: bool
    hit_derivation_cap: bool


@dataclass(frozen=True, slots=True)
class Explanation:
    """The answer to "why is this here?"."""

    triple: dict[str, str]
    rule: str
    premises: list[dict[str, str]]


class ReasonerService:
    """Materialises the inferred graph and reads its provenance back."""

    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime

    @property
    def profile(self) -> Profile:
        return Profile(self.runtime.settings.reasoner)

    # ------------------------------------------------------------------ run

    def run(self, *, profile: Profile | str | None = None) -> ReasonSummary:
        """Rebuild ``urn:ontoforge:inferred`` from scratch."""
        chosen = Profile(profile) if profile is not None else self.profile
        asserted = self._asserted()

        result = materialise(
            asserted,
            profile=chosen,
            max_iterations=self.runtime.settings.reasoner_max_iter,
        )
        self._replace_inferred(result)
        return ReasonSummary(
            profile=chosen.value,
            derived=result.count,
            iterations=result.iterations,
            reached_fixed_point=result.reached_fixed_point,
            hit_derivation_cap=result.hit_derivation_cap,
        )

    def clear(self) -> None:
        self._replace_inferred(ReasoningResult())

    def _asserted(self) -> list[Quad]:
        """What the rules see: the user's own graphs plus any loaded vocabulary."""
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

    def _replace_inferred(self, result: ReasoningResult) -> None:
        existing = list(self.runtime.store.quads_for_pattern(None, None, None, graphs.INFERRED))
        additions = [
            quad for derivation in result.derivations for quad in _derivation_quads(derivation)
        ]
        self.runtime.write(additions=additions, deletions=existing, actor=ACTOR)

    # ------------------------------------------------------------------ read

    def derived_triples(self) -> list[Triple]:
        """The inferred triples themselves, without the provenance records."""
        return [
            quad.object
            for quad in self.runtime.store.quads_for_pattern(
                None, RDF_REIFIES, None, graphs.INFERRED
            )
            if isinstance(quad.object, Triple)
        ]

    def explain(self, triple: Triple) -> Explanation | None:
        """The rule and premises behind a derived triple (§10.1, ``explain_inference``)."""
        for quad in self.runtime.store.quads_for_pattern(
            None, RDF_REIFIES, triple, graphs.INFERRED
        ):
            record = quad.subject
            rule = ""
            premises: list[Triple] = []
            for detail in self.runtime.store.quads_for_pattern(record, None, None, graphs.INFERRED):
                if detail.predicate == ONTF_RULE and isinstance(detail.object, Literal):
                    rule = detail.object.value
                elif detail.predicate == ONTF_PREMISE and isinstance(detail.object, Triple):
                    premises.append(detail.object)
            return Explanation(
                triple=_triple_json(triple),
                rule=rule,
                premises=[_triple_json(premise) for premise in premises],
            )
        return None


def _derivation_quads(derivation: Derivation) -> list[Quad]:
    """The inferred triple, plus the record of how it was reached."""
    record = _record_node(derivation.triple)
    quads = [
        Quad(record, RDF_REIFIES, derivation.triple, graphs.INFERRED),
        Quad(record, ONTF_RULE, Literal(derivation.rule, datatype=XSD_STRING), graphs.INFERRED),
    ]
    quads.extend(
        Quad(record, ONTF_PREMISE, premise, graphs.INFERRED) for premise in derivation.premises
    )
    return quads


def _record_node(triple: Triple) -> NamedNode:
    import hashlib

    digest = hashlib.sha256(str(triple).encode("utf-8")).hexdigest()[:26]
    return NamedNode(f"urn:ontoforge:{DERIVATION_PREFIX}{digest}")


def _triple_json(triple: Triple) -> dict[str, str]:
    from ontoforge.io.graphview import local_name

    return {
        "subject": str(triple.subject),
        "predicate": str(triple.predicate),
        "object": str(triple.object),
        "text": (
            f"{local_name(str(triple.subject))} "
            f"{local_name(str(triple.predicate))} "
            f"{local_name(str(triple.object))}"
        ),
    }
