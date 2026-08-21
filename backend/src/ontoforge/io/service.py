"""Import and export (§8, §11).

Everything written here goes through the change log with an ``import:<file>``
actor, so an import is one undo step and its provenance is on the record.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass, field

from pyoxigraph import DefaultGraph, Literal, NamedNode, Quad, Triple, parse, serialize

from ontoforge.changelog.log import import_actor
from ontoforge.io.csvmap import ONTF_EXTERNAL_KEY, CsvMapping
from ontoforge.io.exporters import to_csv_tables, to_graphml, to_mermaid
from ontoforge.io.formats import (
    ExportFormat,
    ImportFormat,
    format_for_filename,
    is_dataset_format,
    rdf_format,
)
from ontoforge.io.graphview import build_view
from ontoforge.literals import XSD_STRING, make_literal
from ontoforge.namespaces import PREFIXES, RDF_TYPE, RDFS_LABEL
from ontoforge.rdfstar import EdgeMetadata, edge_metadata_quads
from ontoforge.runtime import Runtime
from ontoforge.store import graphs
from ontoforge.store.store import skolemize_quad

#: Refuse anything larger, so one bad file cannot exhaust memory (§13).
DEFAULT_MAX_IMPORT_BYTES = 64 * 1024 * 1024


class UnsupportedFormatError(ValueError):
    """Raised for a format OntoForge does not handle."""


@dataclass(frozen=True, slots=True)
class ImportResult:
    """What an import did."""

    quads: int
    rows: int = 0
    iris: list[str] = field(default_factory=list)
    format: str = ""


class ImportExportService:
    """Reads files into the graph and writes the graph back out."""

    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime

    # ------------------------------------------------------------------ import

    def import_rdf(
        self,
        payload: str | bytes,
        *,
        filename: str,
        import_format: ImportFormat | None = None,
        graph: NamedNode | None = graphs.DATA,
        max_bytes: int = DEFAULT_MAX_IMPORT_BYTES,
    ) -> ImportResult:
        """Load an RDF file. Blank nodes are skolemised so the UI never meets one."""
        raw = payload.encode("utf-8") if isinstance(payload, str) else payload
        if len(raw) > max_bytes:
            raise ValueError(f"the file is too large: {len(raw)} bytes exceeds {max_bytes}")

        resolved = import_format or format_for_filename(filename)
        if resolved is None:
            raise UnsupportedFormatError(f"cannot tell the format of {filename!r}")
        if resolved is ImportFormat.CSV:
            raise UnsupportedFormatError("CSV needs a column mapping; use import_csv")

        serialisation = rdf_format(resolved.value)
        if serialisation is None:  # pragma: no cover - guarded by the enum
            raise UnsupportedFormatError(f"{resolved.value} cannot be parsed as RDF")

        target = None if is_dataset_format(resolved.value) else (graph or graphs.DATA)
        base = self.runtime.settings.base_iri
        try:
            parsed = list(parse(raw, format=serialisation, base_iri=base))
        except (SyntaxError, ValueError) as error:
            raise ValueError(f"could not parse {filename!r}: {error}") from error

        quads = [
            skolemize_quad(
                item if isinstance(item, Quad) else Quad(item.subject, item.predicate, item.object),
                base,
            )
            for item in parsed
        ]
        if target is not None:
            quads = [Quad(q.subject, q.predicate, q.object, target) for q in quads]

        self.runtime.write(additions=quads, actor=import_actor(filename))
        return ImportResult(quads=len(quads), format=resolved.value)

    def import_csv(
        self,
        payload: str | bytes,
        *,
        mapping: CsvMapping,
        filename: str,
        source: str | None = None,
        max_bytes: int = DEFAULT_MAX_IMPORT_BYTES,
    ) -> ImportResult:
        """Load a table: one row becomes one instance, per ``mapping`` (FR-13)."""
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        if len(text.encode("utf-8")) > max_bytes:
            raise ValueError(f"the file is too large: it exceeds {max_bytes} bytes")

        reader = csv.DictReader(io.StringIO(text), delimiter=mapping.delimiter)
        if reader.fieldnames is None:
            raise ValueError("the file has no header row")
        mapping.check_against(list(reader.fieldnames))

        known = self._existing_keys()
        references: dict[str, NamedNode] = dict(known)
        quads: list[Quad] = []
        iris: list[str] = []
        rows = 0

        for row in reader:
            rows += 1
            subject = self._subject_for(row, mapping, known)
            iris.append(subject.value)
            quads.extend(self._row_quads(subject, row, mapping, references, source))

        self.runtime.write(additions=quads, actor=import_actor(filename))
        return ImportResult(quads=len(quads), rows=rows, iris=iris, format="csv")

    # ------------------------------------------------------------------ export

    def export(
        self,
        export_format: ExportFormat | str,
        *,
        named_graphs: Sequence[NamedNode] = graphs.DEFAULT_EXPORT,
    ) -> bytes:
        """Serialise the selected graphs."""
        try:
            resolved = ExportFormat(export_format)
        except ValueError as error:
            raise UnsupportedFormatError(f"unknown export format {export_format!r}") from error

        if resolved in (ExportFormat.GRAPHML, ExportFormat.CSV, ExportFormat.MERMAID):
            view = build_view(self.runtime.store, named_graphs)
            if resolved is ExportFormat.GRAPHML:
                return to_graphml(view)
            if resolved is ExportFormat.CSV:
                return to_csv_tables(view)
            return to_mermaid(view)

        serialisation = rdf_format(resolved.value)
        if serialisation is None:  # pragma: no cover - guarded above
            raise UnsupportedFormatError(f"{resolved.value} has no RDF serialisation")

        quads = [
            quad
            for graph in named_graphs
            for quad in self.runtime.store.quads_for_pattern(None, None, None, graph)
        ]
        if not is_dataset_format(resolved.value):
            # Turtle and RDF/XML cannot carry graph names, so the selected
            # graphs are merged into one document.
            quads = [Quad(q.subject, q.predicate, q.object, DefaultGraph()) for q in quads]

        prefixes = {**PREFIXES, "ont": f"{self.runtime.settings.base_iri}ont#"}
        payload = serialize(quads, format=serialisation, prefixes=prefixes)
        return payload if isinstance(payload, bytes) else str(payload).encode("utf-8")

    # ------------------------------------------------------------------ helpers

    def _existing_keys(self) -> dict[str, NamedNode]:
        """External key to IRI, so a re-import updates rather than duplicates."""
        predicate = NamedNode(ONTF_EXTERNAL_KEY)
        found: dict[str, NamedNode] = {}
        for quad in self.runtime.store.quads_for_pattern(None, predicate, None, graphs.DATA):
            if isinstance(quad.subject, NamedNode) and isinstance(quad.object, Literal):
                found[quad.object.value] = quad.subject
        return found

    def _subject_for(
        self, row: dict[str, str], mapping: CsvMapping, known: dict[str, NamedNode]
    ) -> NamedNode:
        if not mapping.key_column:
            return self.runtime.minter.new_instance()
        key = (row.get(mapping.key_column) or "").strip()
        if not key:
            return self.runtime.minter.new_instance()
        if key not in known:
            known[key] = self.runtime.minter.new_instance()
        return known[key]

    def _reference_for(
        self, predicate: str, cell: str, references: dict[str, NamedNode]
    ) -> tuple[NamedNode, bool]:
        """The node a reference column points at, reused across rows and re-imports."""
        key = _reference_key(predicate, cell)
        if key in references:
            return references[key], False
        minted = self.runtime.minter.new_instance()
        references[key] = minted
        return minted, True

    def _row_quads(
        self,
        subject: NamedNode,
        row: dict[str, str],
        mapping: CsvMapping,
        references: dict[str, NamedNode],
        source: str | None,
    ) -> list[Quad]:
        graph = graphs.DATA
        quads: list[Quad] = []

        label = (row.get(mapping.label_column) or "").strip()
        if label:
            quads.append(Quad(subject, RDFS_LABEL, make_literal(label, language="ja"), graph))
        if mapping.key_column:
            key = (row.get(mapping.key_column) or "").strip()
            if key:
                quads.append(
                    Quad(
                        subject,
                        NamedNode(ONTF_EXTERNAL_KEY),
                        make_literal(key, datatype=XSD_STRING),
                        graph,
                    )
                )
        quads.extend(
            Quad(subject, RDF_TYPE, NamedNode(type_iri), graph) for type_iri in mapping.types
        )

        for column in mapping.columns:
            cell = (row.get(column.column) or "").strip()
            if not cell and column.skip_empty:
                continue
            predicate = NamedNode(column.predicate)
            if column.kind == "reference":
                target, fresh = self._reference_for(column.predicate, cell, references)
                quads.append(Quad(subject, predicate, target, graph))
                if fresh:
                    quads.append(Quad(target, RDFS_LABEL, make_literal(cell, language="ja"), graph))
                    quads.append(
                        Quad(
                            target,
                            NamedNode(ONTF_EXTERNAL_KEY),
                            make_literal(
                                _reference_key(column.predicate, cell), datatype=XSD_STRING
                            ),
                            graph,
                        )
                    )
                if source:
                    quads.extend(
                        edge_metadata_quads(
                            Triple(subject, predicate, target),
                            EdgeMetadata(source=source),
                            graph=graph,
                            base_iri=self.runtime.settings.base_iri,
                        )
                    )
                continue
            quads.append(
                Quad(
                    subject,
                    predicate,
                    make_literal(
                        cell,
                        datatype=NamedNode(column.datatype) if column.datatype else None,
                        language=column.language,
                    ),
                    graph,
                )
            )
        return quads


def _reference_key(predicate: str, cell: str) -> str:
    """The external key of a node created for a reference column."""
    return f"ref:{predicate}:{cell}"
