"""Explaining an inference from the read-only side (§9.2, §10.1).

The reason a triple was derived is not stored anywhere -- owlrl does not produce
one, so it is recovered on demand (:mod:`ontoforge.reasoning.justify`). That
search only reads, which is exactly why it can run here: the MCP handle needs
nothing written for it in advance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyoxigraph import Literal, NamedNode, Triple

from ontoforge.io.graphview import local_name
from ontoforge.namespaces import ONTF, RDF_REIFIES
from ontoforge.reasoning.closure import entails as closure_entails
from ontoforge.reasoning.justify import CLOSURE_STEP, justify
from ontoforge.reasoning.rules import Profile
from ontoforge.store import graphs

if TYPE_CHECKING:  # pragma: no cover
    from ontoforge.mcp.readonly import ReadOnlyGraph

RUN_MARKER = NamedNode("urn:ontoforge:inferred")
ONTF_PROFILE = NamedNode(f"{ONTF}profile")
MAX_CANDIDATES = 400


def _readable(graph: ReadOnlyGraph, triple: Triple) -> dict[str, str]:
    def name(term: object) -> str:
        if isinstance(term, NamedNode):
            label = graph.label_for(term)
            return f"{label} <{term.value}>" if label else f"<{term.value}>"
        if isinstance(term, Literal):
            return f'"{term.value}"'
        return str(term)

    return {
        "subject": str(triple.subject),
        "predicate": str(triple.predicate),
        "object": str(triple.object),
        "text": f"{name(triple.subject)} {local_name(str(triple.predicate))} {name(triple.object)}",
    }


def _profile(graph: ReadOnlyGraph) -> Profile:
    """The profile that produced the graph, so the reason is worked out under it."""
    for quad in graph.store.quads_for_pattern(RUN_MARKER, ONTF_PROFILE, None, graphs.INFERRED):
        if isinstance(quad.object, Literal):
            try:
                return Profile(quad.object.value)
            except ValueError:  # pragma: no cover - a hand-edited graph
                break
    return Profile(graph.settings.reasoner)


def _candidates(graph: ReadOnlyGraph, triple: Triple) -> list[Triple]:
    """The neighbourhood plus the ontology; loaded vocabularies are too large."""
    found: dict[Triple, None] = {}
    for quad in graph.store.quads_for_pattern(None, None, None, graphs.ONTOLOGY):
        found[Triple(quad.subject, quad.predicate, quad.object)] = None
    for end in (triple.subject, triple.object):
        if not isinstance(end, NamedNode):
            continue
        for quad in graph.store.describe(end, depth=2, search=[graphs.DATA]):
            found[Triple(quad.subject, quad.predicate, quad.object)] = None
        for quad in graph.store.quads_for_pattern(None, None, end, graphs.DATA):
            found[Triple(quad.subject, quad.predicate, quad.object)] = None
    return list(found)


def explain_read_only(graph: ReadOnlyGraph, triple: Triple) -> dict[str, Any] | None:
    """Why a derived triple holds, or ``None`` if it was not derived."""
    derived = any(graph.store.quads_for_pattern(None, RDF_REIFIES, triple, graphs.INFERRED))
    if not derived:
        return None

    candidates = _candidates(graph, triple)
    if len(candidates) > MAX_CANDIDATES:
        return {
            "triple": _readable(graph, triple),
            "rule": CLOSURE_STEP,
            "premises": [],
            "explanation": (f"根拠の候補が {len(candidates)} 件あり、探索を打ち切りました。"),
        }

    profile = _profile(graph)
    found = justify(
        triple,
        candidates,
        lambda premises, conclusion: closure_entails(premises, conclusion, profile=profile),
        profile=profile,
    )
    if found is None:
        return {
            "triple": _readable(graph, triple),
            "rule": CLOSURE_STEP,
            "premises": [],
            "explanation": "近傍とオントロジーの範囲では根拠を特定できませんでした。",
        }

    return {
        "triple": _readable(graph, triple),
        "rule": found.rule,
        "premises": [_readable(graph, premise) for premise in found.premises],
        "explanation": (
            f"このトリプルは {found.rule} により、"
            f"{len(found.premises)} 件の前提から導出されました。"
        ),
    }
