from __future__ import annotations

import io
import zipfile

import pytest

from ontoforge.entities import EntityService
from ontoforge.io.csvmap import ColumnMapping, CsvMapping, MappingStore
from ontoforge.io.formats import ExportFormat, ImportFormat, format_for_filename
from ontoforge.io.service import ImportExportService, UnsupportedFormatError
from ontoforge.runtime import Runtime
from ontoforge.store import graphs

PERSON = "https://example.org/kg/ont#Person"
ORGANIZATION = "https://example.org/kg/ont#Organization"
WORKS_FOR = "https://example.org/kg/ont#worksFor"

TURTLE = """
@prefix ex: <https://example.org/kg/id/> .
@prefix ont: <https://example.org/kg/ont#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:alice a ont:Person ; rdfs:label "田中太郎"@ja ; ont:worksFor ex:acme .
ex:acme a ont:Organization ; rdfs:label "株式会社アクメ"@ja .
"""


@pytest.fixture
def service(runtime: Runtime) -> ImportExportService:
    return ImportExportService(runtime)


@pytest.fixture
def populated(service: ImportExportService, runtime: Runtime) -> ImportExportService:
    service.import_rdf(TURTLE, filename="people.ttl")
    return service


# ---------------------------------------------------------------- format lookup


def test_formats_are_recognised_by_filename() -> None:
    assert format_for_filename("people.ttl") is ImportFormat.TURTLE
    assert format_for_filename("people.trig") is ImportFormat.TRIG
    assert format_for_filename("people.jsonld") is ImportFormat.JSONLD
    assert format_for_filename("people.nq") is ImportFormat.NQUADS
    assert format_for_filename("people.nt") is ImportFormat.NTRIPLES
    assert format_for_filename("people.rdf") is ImportFormat.RDFXML
    assert format_for_filename("people.csv") is ImportFormat.CSV


def test_an_unknown_extension_is_reported() -> None:
    assert format_for_filename("people.docx") is None


# ---------------------------------------------------------------- import


def test_turtle_import_lands_in_the_data_graph(
    populated: ImportExportService, runtime: Runtime
) -> None:
    assert runtime.store.count(graphs.DATA) == 5


def test_an_import_is_attributed_to_the_file_it_came_from(
    populated: ImportExportService, runtime: Runtime
) -> None:
    assert runtime.changelog.read_all()[0].actor == "import:people.ttl"


def test_imported_nodes_become_searchable(populated: ImportExportService, runtime: Runtime) -> None:
    assert [hit.iri for hit in runtime.search.search("田中")] == ["https://example.org/kg/id/alice"]


def test_blank_nodes_are_skolemised_on_import(
    service: ImportExportService, runtime: Runtime
) -> None:
    service.import_rdf(
        "<https://example.org/kg/id/a> <https://example.org/kg/ont#addr> [ "
        '<https://example.org/kg/ont#city> "Tokyo" ] .',
        filename="a.ttl",
    )
    objects = [quad.object for quad in runtime.store.quads_for_pattern(None, None, None, None)]
    assert not any(type(term).__name__ == "BlankNode" for term in objects)


def test_an_import_larger_than_the_limit_is_refused(service: ImportExportService) -> None:
    with pytest.raises(ValueError, match="too large"):
        service.import_rdf("x" * 100, filename="big.ttl", max_bytes=10)


def test_an_unsupported_import_format_is_refused(service: ImportExportService) -> None:
    with pytest.raises(UnsupportedFormatError):
        service.import_rdf(TURTLE, filename="people.docx")


def test_malformed_turtle_is_reported_rather_than_swallowed(service: ImportExportService) -> None:
    with pytest.raises(ValueError, match="parse"):
        service.import_rdf("this is not turtle {{{", filename="broken.ttl")


# ---------------------------------------------------------------- export


@pytest.mark.parametrize(
    "export_format",
    [ExportFormat.TURTLE, ExportFormat.TRIG, ExportFormat.JSONLD, ExportFormat.NQUADS],
)
def test_rdf_exports_round_trip(
    populated: ImportExportService, runtime: Runtime, export_format: ExportFormat
) -> None:
    payload = populated.export(export_format)
    runtime.store.clear()
    populated.import_rdf(
        payload.decode("utf-8"),
        filename=f"round.{export_format.value}",
        graph=None if export_format in (ExportFormat.TRIG, ExportFormat.NQUADS) else graphs.DATA,
    )
    assert runtime.store.count(graphs.DATA) == 5


def test_export_defaults_to_the_authored_graphs(populated: ImportExportService) -> None:
    text = populated.export(ExportFormat.TRIG).decode("utf-8")
    assert "urn:ontoforge:data" in text
    assert "urn:ontoforge:layout" not in text


def test_mermaid_export_names_the_nodes_by_label(populated: ImportExportService) -> None:
    text = populated.export(ExportFormat.MERMAID).decode("utf-8")
    assert text.startswith("graph LR")
    assert "田中太郎" in text
    assert "株式会社アクメ" in text
    assert "worksFor" in text


def test_graphml_export_is_well_formed_xml(populated: ImportExportService) -> None:
    from xml.etree import ElementTree

    root = ElementTree.fromstring(populated.export(ExportFormat.GRAPHML).decode("utf-8"))
    assert root.tag.endswith("graphml")
    graph = root.find("{http://graphml.graphdrawing.org/xmlns}graph")
    assert graph is not None
    nodes = graph.findall("{http://graphml.graphdrawing.org/xmlns}node")
    edges = graph.findall("{http://graphml.graphdrawing.org/xmlns}edge")
    assert len(nodes) == 2
    assert len(edges) == 1


def test_csv_export_is_a_zip_of_a_node_table_and_an_edge_table(
    populated: ImportExportService,
) -> None:
    archive = zipfile.ZipFile(io.BytesIO(populated.export(ExportFormat.CSV)))
    assert sorted(archive.namelist()) == ["edges.csv", "nodes.csv"]
    nodes = archive.read("nodes.csv").decode("utf-8")
    assert "田中太郎" in nodes
    assert archive.read("edges.csv").decode("utf-8").count("\n") == 2


def test_export_can_include_the_inferred_graph_on_request(
    populated: ImportExportService, runtime: Runtime
) -> None:
    text = populated.export(ExportFormat.TRIG, named_graphs=[graphs.DATA, graphs.INFERRED]).decode()
    assert "urn:ontoforge:ontology" not in text


def test_an_unsupported_export_format_is_refused(populated: ImportExportService) -> None:
    with pytest.raises(UnsupportedFormatError):
        populated.export("wingdings")  # type: ignore[arg-type]


# ---------------------------------------------------------------- CSV import


CSV_TEXT = "key,name,city,employer\n1,田中太郎,東京,acme\n2,佐藤花子,大阪,acme\n"

MAPPING = CsvMapping(
    name="people",
    key_column="key",
    label_column="name",
    types=[PERSON],
    columns=[
        ColumnMapping(column="city", predicate="https://example.org/kg/ont#city"),
        ColumnMapping(column="employer", predicate=WORKS_FOR, kind="reference"),
    ],
)


def test_csv_import_creates_one_instance_per_row(
    service: ImportExportService, runtime: Runtime
) -> None:
    result = service.import_csv(CSV_TEXT, mapping=MAPPING, filename="people.csv")
    assert result.rows == 2
    assert len(result.iris) == 2
    assert [hit.iri for hit in runtime.search.search("佐藤")] == [result.iris[1]]


def test_csv_columns_become_properties(service: ImportExportService, runtime: Runtime) -> None:
    result = service.import_csv(CSV_TEXT, mapping=MAPPING, filename="people.csv")
    document = EntityService(runtime).get(result.iris[0])
    assert document["https://example.org/kg/ont#city"] == [
        {"@value": "東京", "@type": "http://www.w3.org/2001/XMLSchema#string"}
    ]


def test_a_reference_column_links_rows_that_share_a_value(
    service: ImportExportService, runtime: Runtime
) -> None:
    result = service.import_csv(CSV_TEXT, mapping=MAPPING, filename="people.csv")
    first = EntityService(runtime).get(result.iris[0])
    second = EntityService(runtime).get(result.iris[1])
    assert first[WORKS_FOR] == second[WORKS_FOR]


def test_re_importing_the_same_keys_updates_rather_than_duplicates(
    service: ImportExportService, runtime: Runtime
) -> None:
    first = service.import_csv(CSV_TEXT, mapping=MAPPING, filename="people.csv")
    updated = CSV_TEXT.replace("田中太郎", "田中 太郎")
    second = service.import_csv(updated, mapping=MAPPING, filename="people.csv")
    assert first.iris == second.iris
    assert runtime.search.search("佐藤")


def test_a_csv_import_records_the_source_of_every_edge(
    service: ImportExportService, runtime: Runtime
) -> None:
    service.import_csv(CSV_TEXT, mapping=MAPPING, filename="people.csv", source="file://people.csv")
    from ontoforge.namespaces import PROV_WAS_DERIVED_FROM

    assert list(runtime.store.quads_for_pattern(None, PROV_WAS_DERIVED_FROM, None, None))


def test_a_mapping_naming_a_missing_column_is_rejected(service: ImportExportService) -> None:
    broken = MAPPING.model_copy(update={"label_column": "nope"})
    with pytest.raises(ValueError, match="nope"):
        service.import_csv(CSV_TEXT, mapping=broken, filename="people.csv")


def test_an_empty_csv_is_rejected(service: ImportExportService) -> None:
    with pytest.raises(ValueError, match="header"):
        service.import_csv("", mapping=MAPPING, filename="empty.csv")


def test_tab_separated_input_works(service: ImportExportService) -> None:
    tsv = CSV_TEXT.replace(",", "\t")
    mapping = MAPPING.model_copy(update={"delimiter": "\t"})
    assert service.import_csv(tsv, mapping=mapping, filename="people.tsv").rows == 2


# ---------------------------------------------------------------- mapping store


def test_a_mapping_can_be_saved_and_reused(runtime: Runtime) -> None:
    store = MappingStore(runtime.settings.data_dir / "mappings")
    store.save(MAPPING)
    assert store.names() == ["people"]
    assert store.load("people") == MAPPING


def test_loading_an_unknown_mapping_raises(runtime: Runtime) -> None:
    store = MappingStore(runtime.settings.data_dir / "mappings")
    with pytest.raises(LookupError):
        store.load("nope")


def test_a_mapping_name_may_not_escape_its_directory(runtime: Runtime) -> None:
    store = MappingStore(runtime.settings.data_dir / "mappings")
    with pytest.raises(ValueError, match="name"):
        store.load("../../etc/passwd")
