from __future__ import annotations

from pyoxigraph import RdfFormat

from app.storage.oxigraph_store import OxigraphStore


class ExportService:
    FORMAT_MAP = {
        "turtle": RdfFormat.TURTLE,
        "ttl": RdfFormat.TURTLE,
        "nt": RdfFormat.N_TRIPLES,
        "n-triples": RdfFormat.N_TRIPLES,
        "jsonld": RdfFormat.JSON_LD,
        "json-ld": RdfFormat.JSON_LD,
        "xml": RdfFormat.RDF_XML,
        "rdfxml": RdfFormat.RDF_XML,
    }

    def __init__(self, store: OxigraphStore) -> None:
        self.store = store

    def export(self, fmt: str) -> tuple[bytes, str, str]:
        rdf_format = self.FORMAT_MAP.get(fmt.lower())
        if not rdf_format:
            raise ValueError(f"Unsupported format: {fmt}")
        # Use N-Quads internally for dataset if turtle requested with named graphs
        export_format = rdf_format
        if rdf_format == RdfFormat.TURTLE:
            export_format = RdfFormat.N_QUADS
        content = self.store.export_all(export_format)
        if rdf_format == RdfFormat.TURTLE:
            # Re-serialize via rdflib if available, else return nquads with turtle media type note
            try:
                from rdflib import Graph

                g = Graph()
                g.parse(data=content.decode("utf-8"), format="nquads")
                content = g.serialize(format="turtle").encode("utf-8")
            except Exception:
                content = self.store.export_all(RdfFormat.N_QUADS)
                export_format = RdfFormat.N_QUADS
                rdf_format = RdfFormat.N_QUADS
        media_types = {
            RdfFormat.TURTLE: "text/turtle",
            RdfFormat.N_TRIPLES: "application/n-triples",
            RdfFormat.JSON_LD: "application/ld+json",
            RdfFormat.RDF_XML: "application/rdf+xml",
        }
        extensions = {
            RdfFormat.TURTLE: "ttl",
            RdfFormat.N_TRIPLES: "nt",
            RdfFormat.JSON_LD: "jsonld",
            RdfFormat.RDF_XML: "xml",
        }
        return content, media_types[rdf_format], extensions[rdf_format]
