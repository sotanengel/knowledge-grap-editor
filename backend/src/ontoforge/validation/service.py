"""SHACL validation (§10.2, FR-10).

pySHACL works on rdflib graphs, so the data and the shapes are handed across as
N-Quads and the report comes back as structured findings rather than as another
graph to interpret.

Findings carry a suggested fix, because §7.3-3 asks for exactly that: not
"range violation" but "this relation needs an Organization on the other end --
make Acme an Organization?".
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from pyoxigraph import DefaultGraph, NamedNode, Quad, RdfFormat, Triple, serialize
from rdflib import Graph as RdflibGraph

from ontoforge.io.graphview import local_name
from ontoforge.jsonld import label_of
from ontoforge.namespaces import SH
from ontoforge.runtime import Runtime
from ontoforge.store import graphs
from ontoforge.validation.shapes import ShapeSpec, shape_iri, to_quads

SH_RESULT = f"{SH}result"
SH_FOCUS_NODE = f"{SH}focusNode"
SH_RESULT_PATH = f"{SH}resultPath"
SH_RESULT_MESSAGE = f"{SH}resultMessage"
SH_RESULT_SEVERITY = f"{SH}resultSeverity"
SH_SOURCE_CONSTRAINT = f"{SH}sourceConstraintComponent"
SH_VALUE = f"{SH}value"

ACTOR = "user"


@dataclass(frozen=True, slots=True)
class Finding:
    """One constraint violation, with something the user can act on."""

    focus_node: str
    focus_label: str
    path: str | None
    message: str
    severity: str
    constraint: str
    value: str | None
    suggestion: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "focusNode": self.focus_node,
            "focusLabel": self.focus_label,
            "path": self.path,
            "message": self.message,
            "severity": self.severity,
            "constraint": self.constraint,
            "value": self.value,
            "suggestion": self.suggestion,
        }


@dataclass(slots=True)
class ValidationReport:
    """The whole outcome of one validation run."""

    conforms: bool
    findings: list[Finding] = field(default_factory=list)
    shapes: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "conforms": self.conforms,
            "shapes": self.shapes,
            "findings": [finding.as_dict() for finding in self.findings],
            "violated": sorted({finding.focus_node for finding in self.findings}),
        }


class ValidationService:
    """Runs pySHACL over the store and turns its report into findings."""

    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime

    # ------------------------------------------------------------------ shapes

    def save_shape(self, spec: ShapeSpec, *, actor: str = ACTOR) -> dict[str, Any]:
        """Write a shape, replacing any earlier version of the same name."""
        shape = shape_iri(self.runtime.settings.base_iri, spec.name)
        deletions = self._shape_quads(shape)
        additions = to_quads(spec, base_iri=self.runtime.settings.base_iri)
        self.runtime.write(additions=additions, deletions=deletions, actor=actor)
        return {"@id": shape.value, "quads": len(additions)}

    def delete_shape(self, name: str, *, actor: str = ACTOR) -> int:
        shape = shape_iri(self.runtime.settings.base_iri, name)
        deletions = self._shape_quads(shape)
        self.runtime.write(deletions=deletions, actor=actor)
        return len(deletions)

    def _shape_quads(self, shape: NamedNode) -> list[Quad]:
        """The shape node and its property-shape children."""
        found = list(self.runtime.store.quads_for_pattern(shape, None, None, graphs.SHAPES))
        children = [
            quad.object
            for quad in found
            if isinstance(quad.object, NamedNode)
            and quad.object.value.startswith(f"{shape.value}/")
        ]
        for child in children:
            found.extend(self.runtime.store.quads_for_pattern(child, None, None, graphs.SHAPES))
        return found

    # ------------------------------------------------------------------ run

    def validate(
        self,
        *,
        data_graphs: Sequence[NamedNode] = (graphs.DATA, graphs.ONTOLOGY, graphs.INFERRED),
    ) -> ValidationReport:
        """Check the data against every shape in ``urn:ontoforge:shapes``."""
        shape_quads = list(self.runtime.store.quads_for_pattern(None, None, None, graphs.SHAPES))
        shape_count = sum(1 for quad in shape_quads if quad.predicate.value == f"{SH}targetClass")
        if not shape_quads:
            return ValidationReport(conforms=True, shapes=0)

        data = _to_rdflib(
            quad
            for graph in data_graphs
            for quad in self.runtime.store.quads_for_pattern(None, None, None, graph)
        )
        shapes = _to_rdflib(shape_quads)

        from pyshacl import validate as run_shacl

        conforms, report_graph, _ = run_shacl(
            data_graph=data,
            shacl_graph=shapes,
            # Inference is a separate, explicit step here (§10.1), so pySHACL is
            # told not to quietly run its own.
            inference="none",
            advanced=True,
            meta_shacl=False,
        )
        return ValidationReport(
            conforms=bool(conforms),
            findings=self._findings(report_graph),
            shapes=shape_count,
        )

    def _findings(self, report_graph: RdflibGraph) -> list[Finding]:
        return _findings_from(report_graph, label_for=self._label)

    def _label(self, iri: str) -> str:
        if not iri:
            return ""
        found = label_of(self.runtime.store.quads_for_pattern(NamedNode(iri), None, None, None))
        return found if found is not None else local_name(iri)


def _findings_from(report_graph: RdflibGraph, *, label_for: Callable[[str], str]) -> list[Finding]:
    """Turn a ``sh:ValidationReport`` graph into findings a person can act on."""
    from rdflib import URIRef

    findings: list[Finding] = []
    for result in report_graph.objects(predicate=URIRef(SH_RESULT)):
        details = {
            str(predicate): value for predicate, value in report_graph.predicate_objects(result)
        }
        focus = str(details.get(SH_FOCUS_NODE, ""))
        path = details.get(SH_RESULT_PATH)
        constraint = local_name(str(details.get(SH_SOURCE_CONSTRAINT, "")))
        value = details.get(SH_VALUE)
        focus_label = label_for(focus) if focus else ""
        findings.append(
            Finding(
                focus_node=focus,
                focus_label=focus_label,
                path=str(path) if path is not None else None,
                message=str(details.get(SH_RESULT_MESSAGE, "")),
                severity=local_name(str(details.get(SH_RESULT_SEVERITY, ""))),
                constraint=constraint,
                value=str(value) if value is not None else None,
                suggestion=_suggest(
                    constraint,
                    focus_label,
                    local_name(str(path)) if path is not None else None,
                    str(value) if value is not None else None,
                ),
            )
        )
    return sorted(findings, key=lambda finding: (finding.focus_node, finding.constraint))


def _suggest(constraint: str, focus_label: str, path: str | None, value: str | None) -> str:
    """A repair the user can actually carry out (§7.3-3)."""
    subject = focus_label or "この項目"
    match constraint:
        case "MinCountConstraintComponent":
            return f"「{subject}」に「{path}」を入力してください。"
        case "MaxCountConstraintComponent":
            return f"「{subject}」の「{path}」が多すぎます。余分なものを削除してください。"
        case "DatatypeConstraintComponent":
            return f"「{subject}」の「{path}」の型を見直してください（現在の値: {value}）。"
        case "ClassConstraintComponent":
            return (
                f"「{path}」の相手は指定した種類である必要があります。"
                f"「{value}」の種類を変更しますか？"
            )
        case "NodeKindConstraintComponent":
            return f"「{path}」には項目そのもの（テキストではなく）を指定してください。"
        case "PatternConstraintComponent":
            return f"「{subject}」の「{path}」が決められた書式に合っていません。"
        case "ClosedConstraintComponent":
            return f"「{subject}」に、この種類では認められていない「{path}」が付いています。"
        case _:
            return f"「{subject}」を見直してください。"


def _to_rdflib(quads: Any) -> RdflibGraph:
    """Hand quads to rdflib as N-Triples, which is the cheapest bridge available.

    Quads carrying an RDF 1.2 triple term are left out: rdflib cannot parse
    ``<<( ... )>>``, and SHACL has nothing to say about a reified statement
    anyway. In practice these are the reasoner's provenance records and the
    edge-metadata reifiers, neither of which is data to validate.
    """
    flattened = [
        Quad(q.subject, q.predicate, q.object, DefaultGraph())
        for q in quads
        if not isinstance(q.subject, Triple) and not isinstance(q.object, Triple)
    ]
    payload = serialize(flattened, format=RdfFormat.N_TRIPLES)
    text = payload.decode("utf-8") if isinstance(payload, bytes) else str(payload)
    graph = RdflibGraph()
    graph.parse(data=text, format="nt")
    return graph
