"""Rule-based OWL inference engine."""

from __future__ import annotations

from app.config import settings
from app.ontology.models.triple import Triple, TripleCategory, TripleSource
from app.storage import rdf_constants as R
from app.storage.oxigraph_store import OxigraphStore

SYMMETRIC = f"{R.OWL}SymmetricProperty"
TRANSITIVE = f"{R.OWL}TransitiveProperty"


class InferenceService:
    def __init__(self, store: OxigraphStore) -> None:
        self.store = store

    def infer_all(self) -> list[Triple]:
        inferred: list[Triple] = []
        inferred.extend(self._infer_subclass_types())
        inferred.extend(self._infer_symmetric())
        inferred.extend(self._infer_transitive())
        inferred.extend(self._infer_inverse())
        return self._dedupe(inferred)

    def apply_inferred(self) -> list[Triple]:
        triples = self.infer_all()
        self.store.clear_graph(self.store.inferred_graph)
        for triple in triples:
            self.store.add_triple(triple, self.store.inferred_graph)
        return triples

    def _infer_subclass_types(self) -> list[Triple]:
        sparql = f"""
        PREFIX rdfs: <{R.RDFS}>
        SELECT ?sub ?super WHERE {{
          GRAPH <{settings.ontology_graph}> {{
            ?sub rdfs:subClassOf+ ?super .
          }}
        }}
        """
        subclass_pairs = self.store.query(sparql)
        abox_types = self.store.query(f"""
            SELECT ?s ?type WHERE {{
              GRAPH <{settings.data_graph}> {{
                ?s a ?type .
                FILTER(STRSTARTS(STR(?type), "{R.KG}class:"))
              }}
            }}
        """)
        super_map: dict[str, set[str]] = {}
        for row in subclass_pairs:
            sub = row["sub"]
            sup = row["super"]
            super_map.setdefault(sub, set()).add(sup)
        inferred: list[Triple] = []
        for row in abox_types:
            subject = row["s"]
            direct_type = row["type"]
            supers = super_map.get(direct_type, set())
            for super_type in supers:
                inferred.append(
                    Triple(
                        subject=subject,
                        predicate=R.RDF_TYPE,
                        object=super_type,
                        source=TripleSource.INFERRED,
                        category=TripleCategory.ABOX,
                    )
                )
        return inferred

    def _infer_symmetric(self) -> list[Triple]:
        return self._infer_characteristic(SYMMETRIC, swap=True)

    def _infer_transitive(self) -> list[Triple]:
        props = self._characteristic_properties(TRANSITIVE)
        inferred: list[Triple] = []
        for prop in props:
            edges = self.store.query(f"""
                SELECT ?s ?o WHERE {{
                  GRAPH <{settings.data_graph}> {{
                    ?s <{prop}> ?o .
                  }}
                }}
            """)
            pairs = {(r["s"], r["o"]) for r in edges}
            for a, b in list(pairs):
                for b2, c in pairs:
                    if b == b2 and (a, c) not in pairs:
                        inferred.append(
                            Triple(
                                subject=a,
                                predicate=prop,
                                object=c,
                                source=TripleSource.INFERRED,
                                category=TripleCategory.ABOX,
                            )
                        )
        return inferred

    def _infer_inverse(self) -> list[Triple]:
        inverses = self.store.query(f"""
            PREFIX owl: <{R.OWL}>
            SELECT ?p ?q WHERE {{
              GRAPH <{settings.ontology_graph}> {{
                ?p owl:inverseOf ?q .
              }}
            }}
        """)
        inferred: list[Triple] = []
        for row in inverses:
            p = row["p"]
            q = row["q"]
            for edge in self.store.query(f"""
                SELECT ?s ?o WHERE {{
                  GRAPH <{settings.data_graph}> {{
                    ?s <{p}> ?o .
                  }}
                }}
            """):
                inferred.append(
                    Triple(
                        subject=edge["o"],
                        predicate=q,
                        object=edge["s"],
                        source=TripleSource.INFERRED,
                        category=TripleCategory.ABOX,
                    )
                )
            for edge in self.store.query(f"""
                SELECT ?s ?o WHERE {{
                  GRAPH <{settings.data_graph}> {{
                    ?s <{q}> ?o .
                  }}
                }}
            """):
                inferred.append(
                    Triple(
                        subject=edge["o"],
                        predicate=p,
                        object=edge["s"],
                        source=TripleSource.INFERRED,
                        category=TripleCategory.ABOX,
                    )
                )
        return inferred

    def _infer_characteristic(self, characteristic: str, swap: bool = False) -> list[Triple]:
        props = self._characteristic_properties(characteristic)
        inferred: list[Triple] = []
        for prop in props:
            for edge in self.store.query(f"""
                SELECT ?s ?o WHERE {{
                  GRAPH <{settings.data_graph}> {{
                    ?s <{prop}> ?o .
                  }}
                }}
            """):
                if swap:
                    inferred.append(
                        Triple(
                            subject=edge["o"],
                            predicate=prop,
                            object=edge["s"],
                            source=TripleSource.INFERRED,
                            category=TripleCategory.ABOX,
                        )
                    )
        return inferred

    def _characteristic_properties(self, characteristic: str) -> list[str]:
        rows = self.store.query(f"""
            SELECT ?p WHERE {{
              GRAPH <{settings.ontology_graph}> {{
                ?p a <{characteristic}> .
              }}
            }}
        """)
        return [r["p"] for r in rows]

    @staticmethod
    def _dedupe(triples: list[Triple]) -> list[Triple]:
        seen: set[tuple[str, str, str]] = set()
        unique: list[Triple] = []
        for t in triples:
            key = (t.subject, t.predicate, t.object)
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return unique

    def list_inferred_triples(self) -> list[Triple]:
        rows = self.store.query(f"""
            SELECT ?s ?p ?o WHERE {{
              GRAPH <{settings.inferred_graph}> {{
                ?s ?p ?o .
              }}
            }}
        """)
        return [
            Triple(
                subject=r["s"],
                predicate=r["p"],
                object=r["o"],
                source=TripleSource.INFERRED,
            )
            for r in rows
        ]
