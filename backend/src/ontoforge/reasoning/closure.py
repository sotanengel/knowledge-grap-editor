"""OWL 2 RL materialisation, via owlrl (§5.3, §10.1).

Forward chaining to a fixed point, computed once and written to
``urn:ontoforge:inferred`` so that SPARQL pays nothing for it at query time.

owlrl is what §5.3 names, and using it buys two things the earlier hand-written
rule set could not do:

* **property chains** -- "Alice works for the Tokyo office, the Tokyo office is
  part of Acme, therefore Alice works for Acme";
* **defined classes** -- "anyone working for an Organization is Employed",
  written as ``owl:someValuesFrom`` / ``owl:hasValue`` / ``owl:intersectionOf``.

It also produces a great deal that nobody wants to look at: on a small test
ontology the closure was 185 triples of which 17 concerned the user's own data
and 67 were ``x owl:sameAs x``. Filtering that is :mod:`ontoforge.reasoning.noise`,
deliberately kept separate so the closure itself stays a plain fact about the
graph rather than a matter of taste.
"""

from __future__ import annotations

from collections.abc import Iterable

from owlrl import DeductiveClosure, OWLRL_Semantics, RDFS_Semantics
from pyoxigraph import Quad, Triple

from ontoforge.rdflib_bridge import to_rdflib, triples_from_rdflib
from ontoforge.reasoning.rules import Profile

#: Which owlrl semantics each profile runs. ``rl-lite`` and ``owl2-rl`` share
#: the same engine; they differ in what :mod:`ontoforge.reasoning.noise` keeps.
_SEMANTICS = {
    Profile.RDFS: RDFS_Semantics,
    Profile.RL_LITE: OWLRL_Semantics,
    Profile.OWL2_RL: OWLRL_Semantics,
}


def owl_closure(
    asserted: Iterable[Quad | Triple],
    *,
    profile: Profile | str = Profile.RDFS,
) -> set[Triple]:
    """Everything the profile entails that was not asserted outright."""
    chosen = Profile(profile)
    semantics = _SEMANTICS.get(chosen)
    if semantics is None:
        return set()

    quads = [_as_quad(item) for item in asserted]
    graph = to_rdflib(quads)
    if len(graph) == 0:
        return set()

    before = triples_from_rdflib(graph)
    DeductiveClosure(
        semantics,
        # The axiomatic triples describe RDF and OWL themselves; they say nothing
        # about the user's graph and would swamp it.
        axiomatic_triples=False,
        datatype_axioms=False,
    ).expand(graph)
    return triples_from_rdflib(graph) - before


def entails(asserted: Iterable[Quad | Triple], conclusion: Triple, *, profile: Profile) -> bool:
    """Whether ``conclusion`` follows from ``asserted`` under ``profile``.

    This is the oracle the justification search in :mod:`ontoforge.reasoning.justify`
    calls repeatedly, which is why it stays as small as it can be.
    """
    materialised = list(asserted)
    if conclusion in {_as_triple(item) for item in materialised}:
        return True
    return conclusion in owl_closure(materialised, profile=profile)


def _as_quad(item: Quad | Triple) -> Quad:
    return item if isinstance(item, Quad) else Quad(item.subject, item.predicate, item.object)


def _as_triple(item: Quad | Triple) -> Triple:
    return item if isinstance(item, Triple) else Triple(item.subject, item.predicate, item.object)
