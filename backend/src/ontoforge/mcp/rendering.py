"""Turning graph fragments into what a language model reads best (§9.5).

Turtle is the default because it is shorter than JSON-LD and reads like prose.
Every IRI is accompanied by its label, so a model never has to infer what
`<https://example.org/kg/id/01J8Z…>` refers to.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from pyoxigraph import (
    DefaultGraph,
    NamedNode,
    Quad,
    QuerySolutions,
    RdfFormat,
    Triple,
    serialize,
)

from ontoforge.namespaces import PREFIXES

if TYPE_CHECKING:  # pragma: no cover
    from ontoforge.mcp.readonly import ReadOnlyGraph

MAX_LABEL_COMMENTS = 40


def _prefixes(graph: ReadOnlyGraph) -> dict[str, str]:
    return {
        **PREFIXES,
        "ont": f"{graph.settings.base_iri}ont#",
        "id": f"{graph.settings.base_iri}id/",
    }


def _serialise(graph: ReadOnlyGraph, quads: Sequence[Quad]) -> str:
    payload = serialize(list(quads), format=RdfFormat.TURTLE, prefixes=_prefixes(graph))
    return payload.decode("utf-8") if isinstance(payload, bytes) else str(payload)


def _legend(graph: ReadOnlyGraph, quads: Sequence[Quad]) -> list[str]:
    """A short gloss of the IRIs that appear, so none of them is opaque."""
    seen: dict[str, str] = {}
    for quad in quads:
        for term in (quad.subject, quad.predicate, quad.object):
            if isinstance(term, NamedNode) and term.value not in seen:
                if len(seen) >= MAX_LABEL_COMMENTS:
                    break
                seen[term.value] = graph.label_for(term)
    return [f"# <{iri}> = {label}" for iri, label in seen.items() if label]


def quads_to_turtle(
    graph: ReadOnlyGraph, quads: Sequence[Quad], *, heading: str | None = None
) -> str:
    """Turtle for ``quads``, prefixed with a legend of what each IRI names."""
    if not quads:
        return "# (nothing)"
    flattened = [Quad(q.subject, q.predicate, q.object, DefaultGraph()) for q in quads]
    lines = [heading] if heading else []
    lines.extend(_legend(graph, quads))
    lines.append("")
    lines.append(_serialise(graph, flattened).strip())
    return "\n".join(lines)


def triples_to_turtle(graph: ReadOnlyGraph, triples: Sequence[Triple]) -> str:
    return quads_to_turtle(
        graph, [Quad(t.subject, t.predicate, t.object, DefaultGraph()) for t in triples]
    )


def solutions_to_table(
    graph: ReadOnlyGraph, solutions: QuerySolutions, limit: int
) -> dict[str, Any]:
    """A SELECT result as rows of readable values, capped at ``limit``."""
    variables = [str(variable)[1:] for variable in solutions.variables]
    rows: list[dict[str, Any]] = []
    truncated = False

    for solution in solutions:
        if len(rows) >= limit:
            truncated = True
            break
        row: dict[str, Any] = {}
        for name in variables:
            term = solution[name]
            if term is None:
                continue
            if isinstance(term, NamedNode):
                label = graph.label_for(term)
                row[name] = f"{term.value} ({label})" if label else term.value
            else:
                row[name] = str(getattr(term, "value", term))
        rows.append(row)

    return {"columns": variables, "rows": rows, "count": len(rows), "truncated": truncated}


def entity_lines(graph: ReadOnlyGraph, classes: Sequence[dict[str, Any]]) -> list[str]:
    """A couple of real examples per class, so the schema is not abstract."""
    if not classes:
        return []
    lines = ["", "## Examples", ""]
    for entry in classes[:5]:
        if not entry["instanceCount"]:
            continue
        found = graph.find("", type_iri=entry["iri"], limit=3)
        if not found:
            continue
        names = ", ".join(f"{item.label} `<{item.iri}>`" for item in found)
        lines.append(f"- {entry['label']}: {names}")
    return lines if len(lines) > 3 else []
