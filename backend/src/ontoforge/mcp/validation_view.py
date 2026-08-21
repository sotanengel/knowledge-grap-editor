"""Running SHACL from the read-only side (§9.2 ``validate_graph``).

Validation only ever reads, so it is safe to expose. It reuses the same pySHACL
bridge the API uses, driven from the read-only handle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyoxigraph import NamedNode

from ontoforge.store import graphs
from ontoforge.validation.service import _findings_from, _to_rdflib

if TYPE_CHECKING:  # pragma: no cover
    from ontoforge.mcp.readonly import ReadOnlyGraph

DATA_GRAPHS = (graphs.DATA, graphs.ONTOLOGY, graphs.INFERRED)


def validate_read_only(graph: ReadOnlyGraph, *, shape_name: str | None = None) -> dict[str, Any]:
    """Check the graph against its shapes and report what fails."""
    shape_quads = list(graph.store.quads_for_pattern(None, None, None, graphs.SHAPES))
    if shape_name:
        wanted = f"{graph.settings.base_iri}shape/{shape_name}"
        shape_quads = [
            quad
            for quad in shape_quads
            if isinstance(quad.subject, NamedNode) and quad.subject.value.startswith(wanted)
        ]
        if not shape_quads:
            return {
                "conforms": True,
                "shapes": 0,
                "findings": [],
                "note": f"no shape named {shape_name!r}",
            }
    if not shape_quads:
        return {"conforms": True, "shapes": 0, "findings": [], "note": "no shapes are defined"}

    from pyshacl import validate as run_shacl

    data = _to_rdflib(
        quad
        for named in DATA_GRAPHS
        for quad in graph.store.quads_for_pattern(None, None, None, named)
    )
    conforms, report_graph, _ = run_shacl(
        data_graph=data,
        shacl_graph=_to_rdflib(shape_quads),
        inference="none",
        advanced=True,
        meta_shacl=False,
    )
    findings = _findings_from(report_graph, label_for=lambda iri: graph.label_for(NamedNode(iri)))
    return {
        "conforms": bool(conforms),
        "shapes": sum(1 for quad in shape_quads if quad.predicate.value.endswith("targetClass")),
        "findings": [finding.as_dict() for finding in findings],
    }
