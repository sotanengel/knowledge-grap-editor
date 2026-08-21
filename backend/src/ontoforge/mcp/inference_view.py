"""Reading inference provenance without a writable runtime (§10.1)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyoxigraph import Literal, NamedNode, Triple

from ontoforge.io.graphview import local_name
from ontoforge.namespaces import ONTF, RDF_REIFIES
from ontoforge.store import graphs

if TYPE_CHECKING:  # pragma: no cover
    from ontoforge.mcp.readonly import ReadOnlyGraph

ONTF_RULE = NamedNode(f"{ONTF}rule")
ONTF_PREMISE = NamedNode(f"{ONTF}premise")


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


def explain_read_only(graph: ReadOnlyGraph, triple: Triple) -> dict[str, Any] | None:
    """The rule and premises recorded for a derived triple, or ``None``."""
    for quad in graph.store.quads_for_pattern(None, RDF_REIFIES, triple, graphs.INFERRED):
        rule = ""
        premises: list[Triple] = []
        for detail in graph.store.quads_for_pattern(quad.subject, None, None, graphs.INFERRED):
            if detail.predicate == ONTF_RULE and isinstance(detail.object, Literal):
                rule = detail.object.value
            elif detail.predicate == ONTF_PREMISE and isinstance(detail.object, Triple):
                premises.append(detail.object)
        return {
            "triple": _readable(graph, triple),
            "rule": rule,
            "premises": [_readable(graph, premise) for premise in premises],
            "explanation": (
                f"このトリプルは推論規則 {rule} により、"
                f"{len(premises)} 件の前提から導出されました。"
            ),
        }
    return None
