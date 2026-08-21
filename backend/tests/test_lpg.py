"""The property-graph round trip (§14 Phase 3): out to Gephi or Neo4j, and back."""

from __future__ import annotations

import pytest
from pyoxigraph import Literal, NamedNode, Quad, Triple

from ontoforge.entities import EntityService
from ontoforge.io.formats import ExportFormat, format_for_filename
from ontoforge.io.lpg import LpgParseError, read_csv_tables, read_graphml, round_trip_warnings
from ontoforge.io.service import ImportExportService, UnsupportedFormatError
from ontoforge.literals import XSD_STRING
from ontoforge.namespaces import RDFS_LABEL
from ontoforge.rdfstar import EdgeMetadata, edge_metadata_quads
from ontoforge.runtime import Runtime
from ontoforge.store import graphs

ONT = "https://example.org/kg/ont#"
PERSON = f"{ONT}Person"
WORKS_FOR = f"{ONT}worksFor"
CITY = f"{ONT}city"


@pytest.fixture
def service(runtime: Runtime) -> ImportExportService:
    return ImportExportService(runtime)


@pytest.fixture
def populated(service: ImportExportService, runtime: Runtime) -> tuple[str, str]:
    entities = EntityService(runtime)
    acme = entities.create(label="株式会社アクメ")
    alice = entities.create(
        label="田中太郎",
        types=[PERSON],
        properties={WORKS_FOR: {"@id": acme["@id"]}, CITY: "東京"},
    )
    return alice["@id"], acme["@id"]


# ---------------------------------------------------------------- format lookup


def test_the_return_formats_are_recognised_by_filename() -> None:
    assert format_for_filename("graph.graphml") is not None
    assert format_for_filename("graph.zip") is not None
    # RDF/XML keeps .xml; GraphML does not get to steal it.
    assert format_for_filename("data.xml") is not None
    assert format_for_filename("data.xml").value == "rdfxml"


# ---------------------------------------------------------------- GraphML


def test_graphml_round_trips_nodes_edges_and_attributes(
    service: ImportExportService, runtime: Runtime, populated: tuple[str, str]
) -> None:
    alice, acme = populated
    exported = service.export(ExportFormat.GRAPHML)

    runtime.store.clear()
    result = service.import_lpg(exported, filename="graph.graphml")

    assert result.rows == 2
    assert {node for node in result.iris} == {alice, acme}

    quads = list(runtime.store.quads_for_pattern(None, None, None, graphs.DATA))
    assert Quad(NamedNode(alice), NamedNode(WORKS_FOR), NamedNode(acme), graphs.DATA) in quads
    assert (
        Quad(NamedNode(alice), RDFS_LABEL, Literal("田中太郎", language="ja"), graphs.DATA) in quads
    )
    assert (
        Quad(NamedNode(alice), NamedNode(CITY), Literal("東京", datatype=XSD_STRING), graphs.DATA)
        in quads
    )


def test_graphml_brings_types_back(
    service: ImportExportService, runtime: Runtime, populated: tuple[str, str]
) -> None:
    alice, _ = populated
    exported = service.export(ExportFormat.GRAPHML)
    runtime.store.clear()
    service.import_lpg(exported, filename="graph.graphml")
    assert EntityService(runtime).get(alice)["@type"] == [PERSON]


def test_a_graphml_import_is_attributed_to_its_file(
    service: ImportExportService, runtime: Runtime, populated: tuple[str, str]
) -> None:
    service.import_lpg(service.export(ExportFormat.GRAPHML), filename="from-gephi.graphml")
    assert runtime.changelog.read_all()[-1].actor == "import:from-gephi.graphml"


def test_malformed_graphml_is_reported(service: ImportExportService) -> None:
    with pytest.raises(LpgParseError, match="not valid GraphML"):
        read_graphml("<graphml><unclosed>")


def test_graphml_without_a_graph_element_is_reported(service: ImportExportService) -> None:
    with pytest.raises(LpgParseError, match=r"no <graph>"):
        read_graphml('<graphml xmlns="http://graphml.graphdrawing.org/xmlns" />')


# ---------------------------------------------------------------- CSV tables


def test_the_node_and_edge_tables_round_trip(
    service: ImportExportService, runtime: Runtime, populated: tuple[str, str]
) -> None:
    alice, acme = populated
    exported = service.export(ExportFormat.CSV)

    runtime.store.clear()
    result = service.import_lpg(exported, filename="graph.zip")

    assert result.rows == 2
    quads = list(runtime.store.quads_for_pattern(None, None, None, graphs.DATA))
    assert Quad(NamedNode(alice), NamedNode(WORKS_FOR), NamedNode(acme), graphs.DATA) in quads


def test_an_archive_missing_a_table_is_reported() -> None:
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("nodes.csv", ":ID,label\n")
    with pytest.raises(LpgParseError, match=r"edges\.csv"):
        read_csv_tables(buffer.getvalue())


def test_something_that_is_not_an_archive_is_reported() -> None:
    with pytest.raises(LpgParseError, match="zip archive"):
        read_csv_tables(b"not a zip")


def test_an_unsupported_extension_is_refused(service: ImportExportService) -> None:
    with pytest.raises(UnsupportedFormatError):
        service.import_lpg(b"x", filename="graph.docx")


def test_a_file_over_the_limit_is_refused(service: ImportExportService) -> None:
    with pytest.raises(ValueError, match="too large"):
        service.import_lpg(b"x" * 100, filename="graph.graphml", max_bytes=10)


# ---------------------------------------------------------------- honesty


def test_the_round_trip_warns_about_language_tags(runtime: Runtime) -> None:
    quads = [Quad(NamedNode("https://a"), RDFS_LABEL, Literal("あ", language="ja"), graphs.DATA)]
    assert any("言語タグ" in warning for warning in round_trip_warnings(quads))


def test_the_round_trip_warns_about_edge_metadata(runtime: Runtime) -> None:
    edge = Triple(NamedNode("https://a"), NamedNode(WORKS_FOR), NamedNode("https://b"))
    quads = edge_metadata_quads(edge, EdgeMetadata(confidence=0.5), graph=graphs.DATA)
    assert any("エッジ属性" in warning for warning in round_trip_warnings(quads))


def test_the_round_trip_warns_about_named_graphs(runtime: Runtime) -> None:
    quads = [
        Quad(NamedNode("https://a"), RDFS_LABEL, Literal("a"), graphs.DATA),
        Quad(NamedNode("https://b"), RDFS_LABEL, Literal("b"), graphs.ONTOLOGY),
    ]
    assert any("名前付きグラフ" in warning for warning in round_trip_warnings(quads))


def test_a_plain_graph_produces_no_warnings(runtime: Runtime) -> None:
    quads = [Quad(NamedNode("https://a"), RDFS_LABEL, Literal("a"), graphs.DATA)]
    assert round_trip_warnings(quads) == []


# ---------------------------------------------------------------- over HTTP


def test_a_graphml_upload_goes_through_the_property_graph_reader(runtime: Runtime) -> None:
    from fastapi.testclient import TestClient

    from ontoforge.api.app import create_app

    entities = EntityService(runtime)
    acme = entities.create(label="株式会社アクメ")
    entities.create(label="田中太郎", properties={WORKS_FOR: {"@id": acme["@id"]}})

    with TestClient(create_app(runtime=runtime)) as client:
        exported = client.get("/api/v1/export", params={"format": "graphml"}).content
        runtime.store.clear()

        response = client.post(
            "/api/v1/import",
            files={"file": ("graph.graphml", exported, "application/graphml+xml")},
        )
        assert response.status_code == 200, response.text
        assert response.json()["format"] == "lpg"
        assert response.json()["rows"] == 2


def test_a_node_edge_archive_upload_is_accepted(runtime: Runtime) -> None:
    from fastapi.testclient import TestClient

    from ontoforge.api.app import create_app

    EntityService(runtime).create(label="田中太郎")

    with TestClient(create_app(runtime=runtime)) as client:
        exported = client.get("/api/v1/export", params={"format": "csv"}).content
        runtime.store.clear()

        response = client.post(
            "/api/v1/import", files={"file": ("graph.zip", exported, "application/zip")}
        )
        assert response.status_code == 200, response.text
        assert response.json()["rows"] == 1


def test_a_malformed_property_graph_upload_is_a_400(runtime: Runtime) -> None:
    from fastapi.testclient import TestClient

    from ontoforge.api.app import create_app

    with TestClient(create_app(runtime=runtime)) as client:
        response = client.post(
            "/api/v1/import", files={"file": ("graph.graphml", b"<broken", "text/xml")}
        )
        assert response.status_code == 400
