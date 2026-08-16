from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pyoxigraph import BlankNode, Literal, NamedNode, Quad, RdfFormat, Store, Variable

from app.config import settings
from app.ontology.models.triple import Triple
from app.storage import rdf_constants as R


class OxigraphStore:
    """Oxigraph-backed RDF store with named graph separation."""

    def __init__(self, data_dir: str | None = None) -> None:
        self.data_dir = data_dir or settings.data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        db_path = os.path.join(self.data_dir, "oxigraph")
        self.store = Store(db_path)
        self.ontology_graph = NamedNode(settings.ontology_graph)
        self.data_graph = NamedNode(settings.data_graph)
        self.inferred_graph = NamedNode(settings.inferred_graph)
        self._seed_loaded_marker = os.path.join(self.data_dir, ".seed_loaded")

    def _named_node(self, uri: str) -> NamedNode | BlankNode:
        if uri.startswith("_:"):
            return BlankNode(uri[2:])
        return NamedNode(uri)

    def _object_term(self, uri: str) -> NamedNode | BlankNode:
        return self._named_node(uri)

    def load_seed_if_needed(self, seed_path: Path) -> None:
        if os.path.exists(self._seed_loaded_marker):
            return
        if not seed_path.exists():
            return
        self.store.bulk_load(
            path=str(seed_path),
            format=RdfFormat.TURTLE,
            to_graph=self.ontology_graph,
        )
        with open(self._seed_loaded_marker, "w", encoding="utf-8") as f:
            f.write(datetime.now(UTC).isoformat())

    def add_quad(
        self,
        subject: str,
        predicate: str,
        obj: str | Literal,
        graph: NamedNode,
    ) -> None:
        s = self._named_node(subject)
        p = NamedNode(predicate)
        o: NamedNode | BlankNode | Literal = (
            obj if isinstance(obj, Literal) else self._object_term(obj)
        )
        self.store.add(Quad(s, p, o, graph))

    def add_triple(self, triple: Triple, graph: NamedNode) -> None:
        if triple.object_is_literal:
            lit = self.literal(
                triple.object,
                triple.literal_datatype,
            )
            if triple.literal_language:
                lit = Literal(triple.object, language=triple.literal_language)
            self.add_quad(triple.subject, triple.predicate, lit, graph)
        else:
            self.add_quad(triple.subject, triple.predicate, triple.object, graph)

    def remove_entity_quads(self, entity_uri: str, graph: NamedNode) -> None:
        entity = self._named_node(entity_uri)
        to_remove: list[Quad] = []
        for quad in self.store.quads_for_pattern(entity, None, None, graph):
            to_remove.append(quad)
        for quad in self.store.quads_for_pattern(None, None, entity, graph):
            to_remove.append(quad)
        for quad in to_remove:
            self.store.remove(quad)

    @staticmethod
    def _term_str(term: Any) -> str:
        if term is None:
            return ""
        if hasattr(term, "value"):
            return str(term.value)
        return str(term)

    def query(self, sparql: str) -> list[dict[str, str]]:
        var_match = re.search(r"SELECT\s+(.*?)\s+WHERE", sparql, re.IGNORECASE | re.DOTALL)
        vars_raw = var_match.group(1) if var_match else ""
        var_names = re.findall(r"\?(\w+)", vars_raw)
        results: list[dict[str, str]] = []
        for solution in self.store.query(sparql):
            row: dict[str, str] = {}
            for name in var_names:
                term = solution[Variable(name)]
                row[name] = self._term_str(term)
            results.append(row)
        return results

    def literal(
        self,
        value: Any,
        datatype: str | None = None,
        language: str | None = None,
    ) -> Literal:
        if language:
            return Literal(str(value), language=language)
        if datatype:
            return Literal(str(value), datatype=NamedNode(datatype))
        if isinstance(value, bool):
            return Literal(str(value).lower(), datatype=NamedNode(f"{R.XSD}boolean"))
        if isinstance(value, int):
            return Literal(str(value), datatype=NamedNode(f"{R.XSD}integer"))
        if isinstance(value, float):
            return Literal(str(value), datatype=NamedNode(f"{R.XSD}decimal"))
        return Literal(str(value))

    def now_literal(self) -> Literal:
        return Literal(datetime.now(UTC).isoformat(), datatype=NamedNode(f"{R.XSD}dateTime"))

    def clear_graph(self, graph: NamedNode) -> None:
        to_remove = list(self.store.quads_for_pattern(None, None, None, graph))
        for quad in to_remove:
            self.store.remove(quad)

    def export_all(self, fmt: RdfFormat) -> bytes:
        return self.store.dump(format=fmt)
