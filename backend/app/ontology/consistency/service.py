"""OWL consistency checking."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import settings
from app.ontology.inference.service import InferenceService
from app.storage import rdf_constants as R
from app.storage.oxigraph_store import OxigraphStore

FUNCTIONAL = f"{R.OWL}FunctionalProperty"


@dataclass
class Inconsistency:
    code: str
    message: str
    involved_iris: list[str] = field(default_factory=list)


@dataclass
class ConsistencyReport:
    consistent: bool
    inconsistencies: list[Inconsistency] = field(default_factory=list)


class ConsistencyService:
    def __init__(self, store: OxigraphStore, inference: InferenceService) -> None:
        self.store = store
        self.inference = inference

    def check(self) -> ConsistencyReport:
        issues: list[Inconsistency] = []
        issues.extend(self._check_disjoint_classes())
        issues.extend(self._check_functional_properties())
        issues.extend(self._check_same_as_different_from())
        return ConsistencyReport(consistent=len(issues) == 0, inconsistencies=issues)

    def _check_disjoint_classes(self) -> list[Inconsistency]:
        rows = self.store.query(f"""
            PREFIX owl: <{R.OWL}>
            SELECT ?a ?b ?x WHERE {{
              GRAPH <{settings.ontology_graph}> {{
                ?a owl:disjointWith ?b .
              }}
              GRAPH <{settings.data_graph}> {{
                ?x a ?a .
                ?x a ?b .
              }}
            }}
        """)
        return [
            Inconsistency(
                code="DISJOINT_CLASS_VIOLATION",
                message=f"Individual belongs to disjoint classes {r['a']} and {r['b']}",
                involved_iris=[r["x"], r["a"], r["b"]],
            )
            for r in rows
        ]

    def _check_functional_properties(self) -> list[Inconsistency]:
        functional_props = self.store.query(f"""
            SELECT ?p WHERE {{
              GRAPH <{settings.ontology_graph}> {{
                ?p a <{FUNCTIONAL}> .
              }}
            }}
        """)
        issues: list[Inconsistency] = []
        for row in functional_props:
            prop = row["p"]
            violations = self.store.query(f"""
                SELECT ?s ?o1 ?o2 WHERE {{
                  GRAPH <{settings.data_graph}> {{
                    ?s <{prop}> ?o1 .
                    ?s <{prop}> ?o2 .
                    FILTER(?o1 != ?o2)
                  }}
                }}
            """)
            for v in violations:
                issues.append(
                    Inconsistency(
                        code="FUNCTIONAL_PROPERTY_VIOLATION",
                        message=(
                            f"Functional property {prop} has distinct values "
                            f"for the same subject"
                        ),
                        involved_iris=[v["s"], prop, v["o1"], v["o2"]],
                    )
                )
        return issues

    def _check_same_as_different_from(self) -> list[Inconsistency]:
        rows = self.store.query(f"""
            PREFIX owl: <{R.OWL}>
            SELECT ?a ?b WHERE {{
              GRAPH <{settings.data_graph}> {{
                ?a owl:sameAs ?b .
                ?a owl:differentFrom ?b .
              }}
            }}
        """)
        return [
            Inconsistency(
                code="SAME_AND_DIFFERENT",
                message=f"Individual {r['a']} is both sameAs and differentFrom {r['b']}",
                involved_iris=[r["a"], r["b"]],
            )
            for r in rows
        ]
