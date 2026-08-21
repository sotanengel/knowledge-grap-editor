"""Non-RDF exports: GraphML, node/edge CSV and Mermaid (§11)."""

from __future__ import annotations

import csv
import io
import re
import zipfile
from xml.etree import ElementTree as ET

from ontoforge.io.graphview import GraphView, local_name

GRAPHML_NS = "http://graphml.graphdrawing.org/xmlns"
NODES_FILENAME = "nodes.csv"
EDGES_FILENAME = "edges.csv"

_MERMAID_ID = re.compile(r"[^A-Za-z0-9_]")


# ---------------------------------------------------------------------- GraphML


def to_graphml(view: GraphView) -> bytes:
    """A GraphML document Gephi and yEd can open."""
    ET.register_namespace("", GRAPHML_NS)
    root = ET.Element(f"{{{GRAPHML_NS}}}graphml")

    keys = ["label", "types", *view.attribute_keys]
    for index, key in enumerate(keys):
        ET.SubElement(
            root,
            f"{{{GRAPHML_NS}}}key",
            {"id": f"n{index}", "for": "node", "attr.name": key, "attr.type": "string"},
        )
    ET.SubElement(
        root,
        f"{{{GRAPHML_NS}}}key",
        {"id": "e0", "for": "edge", "attr.name": "label", "attr.type": "string"},
    )
    ET.SubElement(
        root,
        f"{{{GRAPHML_NS}}}key",
        {"id": "e1", "for": "edge", "attr.name": "predicate", "attr.type": "string"},
    )

    graph = ET.SubElement(root, f"{{{GRAPHML_NS}}}graph", {"id": "G", "edgedefault": "directed"})
    key_ids = {key: f"n{index}" for index, key in enumerate(keys)}

    for node in view.nodes:
        element = ET.SubElement(graph, f"{{{GRAPHML_NS}}}node", {"id": node.iri})
        _data(element, key_ids["label"], node.label)
        if node.types:
            _data(element, key_ids["types"], " ".join(node.types))
        for key, values in sorted(node.attributes.items()):
            _data(element, key_ids[key], " ".join(values))

    for index, edge in enumerate(view.edges):
        element = ET.SubElement(
            graph,
            f"{{{GRAPHML_NS}}}edge",
            {"id": f"e{index}", "source": edge.source, "target": edge.target},
        )
        _data(element, "e0", edge.label)
        _data(element, "e1", edge.predicate)

    payload: bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return payload


def _data(parent: ET.Element, key: str, text: str) -> None:
    element = ET.SubElement(parent, f"{{{GRAPHML_NS}}}data", {"key": key})
    element.text = text


# ---------------------------------------------------------------------- CSV pair


def to_csv_tables(view: GraphView) -> bytes:
    """A zip holding a node table and an edge table, in Neo4j's usual shape."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(NODES_FILENAME, _nodes_csv(view))
        archive.writestr(EDGES_FILENAME, _edges_csv(view))
    return buffer.getvalue()


def _nodes_csv(view: GraphView) -> str:
    attribute_keys = view.attribute_keys
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow([":ID", "label", ":LABEL", *attribute_keys])
    for node in view.nodes:
        writer.writerow(
            [
                node.iri,
                node.label,
                ";".join(local_name(type_iri) for type_iri in node.types),
                *[" ".join(node.attributes.get(key, [])) for key in attribute_keys],
            ]
        )
    return out.getvalue()


def _edges_csv(view: GraphView) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow([":START_ID", ":END_ID", ":TYPE", "predicate"])
    for edge in view.edges:
        writer.writerow([edge.source, edge.target, edge.label, edge.predicate])
    return out.getvalue()


# ---------------------------------------------------------------------- Mermaid


def to_mermaid(view: GraphView, *, max_nodes: int = 200) -> bytes:
    """A Mermaid flowchart, for pasting into documentation."""
    nodes = view.nodes[:max_nodes]
    kept = {node.iri for node in nodes}
    identifiers = {node.iri: _mermaid_id(node.iri, index) for index, node in enumerate(nodes)}

    lines = ["graph LR"]
    lines.extend(f'    {identifiers[node.iri]}["{_escape(node.label)}"]' for node in nodes)
    lines.extend(
        f"    {identifiers[edge.source]} -->|{_escape(edge.label)}| {identifiers[edge.target]}"
        for edge in view.edges
        if edge.source in kept and edge.target in kept
    )
    if len(view.nodes) > max_nodes:
        lines.append(f"    %% {len(view.nodes) - max_nodes} further node(s) omitted")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _mermaid_id(iri: str, index: int) -> str:
    cleaned = _MERMAID_ID.sub("_", local_name(iri))[:40]
    return f"n{index}_{cleaned}" if cleaned else f"n{index}"


def _escape(text: str) -> str:
    return text.replace('"', "'").replace("\n", " ")
