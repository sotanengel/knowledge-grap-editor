"""The MCP surface must be read-only. These tests are the proof of FR-16."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from pyoxigraph import Literal, NamedNode, Quad

from ontoforge.config import Settings
from ontoforge.mcp.readonly import ReadOnlyGraph
from ontoforge.mcp.server import create_server
from ontoforge.namespaces import RDF_TYPE, RDFS_LABEL, RDFS_SUBCLASS_OF
from ontoforge.reasoning.service import ReasonerService
from ontoforge.runtime import Runtime
from ontoforge.store import graphs
from ontoforge.store.store import ReadOnlyStoreError
from ontoforge.validation.service import ValidationService
from ontoforge.validation.shapes import PropertyConstraint, ShapeSpec

ONT = "https://example.org/kg/ont#"
ID = "https://example.org/kg/id/"

PERSON = NamedNode(f"{ONT}Person")
EMPLOYEE = NamedNode(f"{ONT}Employee")
ORGANIZATION = NamedNode(f"{ONT}Organization")
WORKS_FOR = NamedNode(f"{ONT}worksFor")
ALICE = NamedNode(f"{ID}alice")
ACME = NamedNode(f"{ID}acme")
BOB = NamedNode(f"{ID}bob")

UPDATES = [
    "INSERT DATA { <https://a> <https://b> <https://c> }",
    "DELETE WHERE { ?s ?p ?o }",
    "CLEAR ALL",
    "DROP GRAPH <urn:ontoforge:data>",
    "LOAD <https://evil.example/x.ttl>",
    "SELECT ?s WHERE { ?s ?p ?o } ; INSERT DATA { <https://a> <https://b> <https://c> }",
]


@pytest.fixture
def populated(settings: Settings) -> Settings:
    """A store with a small graph, closed again so it can be reopened read-only."""
    with Runtime.create(settings) as runtime:
        runtime.write(
            additions=[
                Quad(
                    PERSON,
                    RDF_TYPE,
                    NamedNode("http://www.w3.org/2002/07/owl#Class"),
                    graphs.ONTOLOGY,
                ),
                Quad(PERSON, RDFS_LABEL, Literal("人物", language="ja"), graphs.ONTOLOGY),
                Quad(
                    EMPLOYEE,
                    RDF_TYPE,
                    NamedNode("http://www.w3.org/2002/07/owl#Class"),
                    graphs.ONTOLOGY,
                ),
                Quad(EMPLOYEE, RDFS_LABEL, Literal("社員", language="ja"), graphs.ONTOLOGY),
                Quad(EMPLOYEE, RDFS_SUBCLASS_OF, PERSON, graphs.ONTOLOGY),
                Quad(
                    ORGANIZATION,
                    RDF_TYPE,
                    NamedNode("http://www.w3.org/2002/07/owl#Class"),
                    graphs.ONTOLOGY,
                ),
                Quad(ORGANIZATION, RDFS_LABEL, Literal("組織", language="ja"), graphs.ONTOLOGY),
                Quad(
                    WORKS_FOR,
                    RDF_TYPE,
                    NamedNode("http://www.w3.org/2002/07/owl#ObjectProperty"),
                    graphs.ONTOLOGY,
                ),
                Quad(WORKS_FOR, RDFS_LABEL, Literal("所属", language="ja"), graphs.ONTOLOGY),
                Quad(
                    WORKS_FOR,
                    NamedNode("http://www.w3.org/2000/01/rdf-schema#domain"),
                    PERSON,
                    graphs.ONTOLOGY,
                ),
                Quad(
                    WORKS_FOR,
                    NamedNode("http://www.w3.org/2000/01/rdf-schema#range"),
                    ORGANIZATION,
                    graphs.ONTOLOGY,
                ),
                Quad(ALICE, RDF_TYPE, EMPLOYEE, graphs.DATA),
                Quad(ALICE, RDFS_LABEL, Literal("田中太郎", language="ja"), graphs.DATA),
                Quad(ALICE, WORKS_FOR, ACME, graphs.DATA),
                Quad(ACME, RDF_TYPE, ORGANIZATION, graphs.DATA),
                Quad(ACME, RDFS_LABEL, Literal("株式会社アクメ", language="ja"), graphs.DATA),
                Quad(BOB, RDF_TYPE, EMPLOYEE, graphs.DATA),
                Quad(BOB, RDFS_LABEL, Literal("佐藤花子", language="ja"), graphs.DATA),
                Quad(BOB, WORKS_FOR, ACME, graphs.DATA),
            ]
        )
        ReasonerService(runtime).run(profile="rdfs")
        ValidationService(runtime).save_shape(
            ShapeSpec(
                name="person",
                target_class=PERSON.value,
                properties=[PropertyConstraint(path=f"{ONT}birthDate", min_count=1)],
            )
        )
    return settings


@pytest.fixture
def graph(populated: Settings) -> Iterator[ReadOnlyGraph]:
    with ReadOnlyGraph.open(populated) as opened:
        yield opened


@dataclass(frozen=True)
class ToolOutcome:
    """A uniform view of a tool call, whether it succeeded or was refused."""

    error: str | None = None
    structured: dict | None = None
    text: str = ""

    @property
    def is_error(self) -> bool:
        return self.error is not None


async def _call(graph: ReadOnlyGraph, name: str, **arguments: object) -> ToolOutcome:
    from mcp.server.mcpserver.exceptions import ToolError as SdkToolError

    server = create_server(graph)
    try:
        result = await server.call_tool(name, arguments)
    except SdkToolError as error:
        return ToolOutcome(error=str(error))
    text = "".join(
        str(block.text) for block in result.content if getattr(block, "text", None) is not None
    )
    return ToolOutcome(structured=result.structured_content, text=text)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# ---------------------------------------------------------------- FR-16 layer 1


@pytest.mark.anyio
async def test_no_tool_can_write(graph: ReadOnlyGraph) -> None:
    server = create_server(graph)
    names = {tool.name for tool in await server.list_tools()}
    assert names == {
        "search_entities",
        "get_entity",
        "list_classes",
        "list_properties",
        "describe_ontology",
        "get_neighbors",
        "find_path",
        "sparql_select",
        "validate_graph",
        "explain_inference",
    }
    forbidden = {"create", "update", "delete", "insert", "write", "patch", "add", "remove", "set"}
    assert not any(word in name for name in names for word in forbidden)


# ---------------------------------------------------------------- FR-16 layer 2


def test_the_store_is_opened_read_only(graph: ReadOnlyGraph) -> None:
    assert graph.store.read_only is True


def test_the_store_layer_itself_refuses_a_write(graph: ReadOnlyGraph) -> None:
    with pytest.raises(ReadOnlyStoreError):
        graph.store.add([Quad(ALICE, RDFS_LABEL, Literal("なりすまし"), graphs.DATA)])
    with pytest.raises(ReadOnlyStoreError):
        graph.store.update("CLEAR ALL")
    with pytest.raises(ReadOnlyStoreError):
        graph.store.clear_graph(graphs.DATA)


def test_a_writable_store_cannot_be_used_for_mcp(settings: Settings) -> None:
    with Runtime.create(settings) as runtime, pytest.raises(ValueError, match="read-only"):
        ReadOnlyGraph(runtime.store, runtime.search, settings)


def test_opening_without_a_store_says_so(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ReadOnlyGraph.open(Settings(data_dir=tmp_path / "absent"))


# ---------------------------------------------------------------- FR-16 layer 3


@pytest.mark.anyio
@pytest.mark.parametrize("query", UPDATES)
async def test_sparql_select_refuses_every_update_form(graph: ReadOnlyGraph, query: str) -> None:
    result = await _call(graph, "sparql_select", query=query)
    assert result.is_error
    assert "refused" in str(result.error).lower()


@pytest.mark.anyio
async def test_the_graph_is_unchanged_after_a_refused_update(graph: ReadOnlyGraph) -> None:
    before = graph.store.count()
    for query in UPDATES:
        await _call(graph, "sparql_select", query=query)
    assert graph.store.count() == before


# ---------------------------------------------------------------- reading


@pytest.mark.anyio
async def test_search_entities_finds_by_label(graph: ReadOnlyGraph) -> None:
    result = await _call(graph, "search_entities", query="田中")
    assert result.structured["count"] == 1
    assert result.structured["entities"][0]["label"] == "田中太郎"


@pytest.mark.anyio
async def test_get_entity_returns_turtle_with_labels_for_every_iri(
    graph: ReadOnlyGraph,
) -> None:
    turtle = (await _call(graph, "get_entity", iri=ALICE.value)).text
    assert "田中太郎" in turtle
    # Every IRI is glossed, so a model never sees a bare identifier (§9.5).
    assert f"# <{ACME.value}> = 株式会社アクメ" in turtle


@pytest.mark.anyio
async def test_get_entity_on_an_unknown_iri_is_an_error(graph: ReadOnlyGraph) -> None:
    assert (await _call(graph, "get_entity", iri=f"{ID}nobody")).is_error


@pytest.mark.anyio
async def test_list_classes_reports_instance_counts(graph: ReadOnlyGraph) -> None:
    classes = (await _call(graph, "list_classes")).structured["classes"]
    by_label = {entry["label"]: entry for entry in classes}
    assert by_label["社員"]["instanceCount"] == 2


@pytest.mark.anyio
async def test_list_classes_can_be_rooted(graph: ReadOnlyGraph) -> None:
    result = await _call(graph, "list_classes", root=PERSON.value)
    assert {entry["label"] for entry in result.structured["classes"]} == {"人物", "社員"}


@pytest.mark.anyio
async def test_list_properties_reports_domain_and_range(graph: ReadOnlyGraph) -> None:
    (prop,) = (await _call(graph, "list_properties")).structured["properties"]
    assert prop["domain"] == [PERSON.value]
    assert prop["range"] == [ORGANIZATION.value]


@pytest.mark.anyio
async def test_describe_ontology_hands_over_the_schema_first(graph: ReadOnlyGraph) -> None:
    summary = (await _call(graph, "describe_ontology")).text
    assert "## Classes" in summary
    assert "人物" in summary and "所属" in summary
    assert "instance(s)" in summary
    assert "田中太郎" in summary  # worked examples, so the schema is not abstract


@pytest.mark.anyio
async def test_get_neighbors_returns_the_surrounding_subgraph(graph: ReadOnlyGraph) -> None:
    result = (await _call(graph, "get_neighbors", iri=ACME.value, depth=1)).structured
    assert {node["iri"] for node in result["nodes"]} == {ACME.value, ALICE.value, BOB.value}
    assert all(edge["predicateLabel"] == "所属" for edge in result["edges"])


@pytest.mark.anyio
async def test_get_neighbors_respects_its_cap(graph: ReadOnlyGraph) -> None:
    result = (await _call(graph, "get_neighbors", iri=ACME.value, depth=3, max_nodes=2)).structured
    assert len(result["nodes"]) <= 2
    assert result["truncated"]


@pytest.mark.anyio
async def test_find_path_walks_between_two_nodes(graph: ReadOnlyGraph) -> None:
    result = (await _call(graph, "find_path", from_iri=ALICE.value, to_iri=BOB.value)).structured
    assert result["found"]
    assert result["hops"] == 2
    assert result["path"][0]["predicateLabel"] == "所属"


@pytest.mark.anyio
async def test_find_path_says_so_when_there_is_none(graph: ReadOnlyGraph) -> None:
    result = (
        await _call(graph, "find_path", from_iri=ALICE.value, to_iri=f"{ID}nobody")
    ).structured
    assert result["found"] is False


@pytest.mark.anyio
async def test_sparql_select_returns_a_labelled_table(graph: ReadOnlyGraph) -> None:
    result = (
        await _call(
            graph,
            "sparql_select",
            query=(
                f"SELECT ?s WHERE {{ GRAPH <{graphs.DATA.value}> "
                f"{{ ?s a <{ORGANIZATION.value}> }} }}"
            ),
        )
    ).structured
    assert result["form"] == "SELECT"
    assert "株式会社アクメ" in result["rows"][0]["s"]


@pytest.mark.anyio
async def test_sparql_select_caps_its_result_size(graph: ReadOnlyGraph) -> None:
    result = (
        await _call(
            graph, "sparql_select", query="SELECT ?s WHERE { GRAPH ?g { ?s ?p ?o } }", limit=2
        )
    ).structured
    assert result["count"] == 2
    assert result["truncated"]


@pytest.mark.anyio
async def test_an_ask_query_comes_back_as_a_boolean(graph: ReadOnlyGraph) -> None:
    # Everything lives in named graphs, so the default graph is genuinely empty.
    inside = await _call(graph, "sparql_select", query="ASK { GRAPH ?g { ?s ?p ?o } }")
    outside = await _call(graph, "sparql_select", query="ASK { ?s ?p ?o }")
    assert inside.structured == {"form": "ASK", "boolean": True}
    assert outside.structured == {"form": "ASK", "boolean": False}


@pytest.mark.anyio
async def test_a_construct_query_comes_back_as_turtle(graph: ReadOnlyGraph) -> None:
    result = (
        await _call(
            graph,
            "sparql_select",
            query=(
                f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ GRAPH <{graphs.DATA.value}> {{ ?s ?p ?o }} }}"
            ),
        )
    ).structured
    assert result["form"] == "CONSTRUCT"
    assert "田中太郎" in result["turtle"]


@pytest.mark.anyio
async def test_validate_graph_reports_the_shape_violations(graph: ReadOnlyGraph) -> None:
    result = (await _call(graph, "validate_graph")).structured
    assert result["conforms"] is False
    assert any("田中太郎" in finding["suggestion"] for finding in result["findings"])


@pytest.mark.anyio
async def test_validate_graph_can_target_one_shape(graph: ReadOnlyGraph) -> None:
    assert (await _call(graph, "validate_graph", shape="nope")).structured["shapes"] == 0


@pytest.mark.anyio
async def test_explain_inference_names_the_rule_and_premises(graph: ReadOnlyGraph) -> None:
    result = (
        await _call(
            graph,
            "explain_inference",
            subject=ALICE.value,
            predicate=RDF_TYPE.value,
            object=PERSON.value,
        )
    ).structured
    # Alice is a Person twice over: she is an Employee, and `worksFor` has
    # Person as its domain. Either route is a complete answer, so what matters
    # is that the premises are real and the step is named.
    assert result["rule"] in {"rdfs:subClassOf-type", "rdfs:domain"}
    assert result["premises"]
    assert "田中太郎" in result["triple"]["text"]
    assert all(premise["text"] for premise in result["premises"])


@pytest.mark.anyio
async def test_explaining_an_asserted_triple_is_an_error(graph: ReadOnlyGraph) -> None:
    result = await _call(
        graph,
        "explain_inference",
        subject=ALICE.value,
        predicate=RDF_TYPE.value,
        object=EMPLOYEE.value,
    )
    assert result.is_error


# ---------------------------------------------------------------- resources & prompts


@pytest.mark.anyio
async def test_the_four_resources_are_published(graph: ReadOnlyGraph) -> None:
    server = create_server(graph)
    assert {str(resource.uri) for resource in await server.list_resources()} == {
        "ontoforge://ontology/schema.ttl",
        "ontoforge://ontology/summary.md",
        "ontoforge://graphs",
        "ontoforge://examples/queries.md",
    }


@pytest.mark.anyio
async def test_the_schema_resource_is_turtle(graph: ReadOnlyGraph) -> None:
    server = create_server(graph)
    (content,) = await server.read_resource("ontoforge://ontology/schema.ttl")
    assert "人物" in str(content.content)


@pytest.mark.anyio
async def test_the_example_queries_use_this_graphs_own_terms(graph: ReadOnlyGraph) -> None:
    server = create_server(graph)
    (content,) = await server.read_resource("ontoforge://examples/queries.md")
    assert ORGANIZATION.value in str(content.content) or PERSON.value in str(content.content)


@pytest.mark.anyio
async def test_the_three_prompts_are_published(graph: ReadOnlyGraph) -> None:
    server = create_server(graph)
    assert {prompt.name for prompt in await server.list_prompts()} == {
        "explore_entity",
        "build_sparql",
        "extract_to_kg",
    }


@pytest.mark.anyio
async def test_extract_to_kg_tells_the_model_it_cannot_write(graph: ReadOnlyGraph) -> None:
    server = create_server(graph)
    result = await server.get_prompt("extract_to_kg", {"document": "アクメは東京にある。"})
    text = str(result.messages[0].content.text)
    assert "cannot write" in text
    assert "アクメは東京にある。" in text


# ---------------------------------------------------------------- the in-process mount


def test_a_shared_read_only_view_still_refuses_every_write(settings: Settings) -> None:
    # The HTTP mount shares the API's handle, because a second pyoxigraph handle
    # on a live database is undefined behaviour. The refusal moves to the wrapper.
    with Runtime.create(settings) as runtime:
        shared = ReadOnlyGraph.sharing(runtime.store, runtime.search, settings)
        assert shared.store.read_only is True
        with pytest.raises(ReadOnlyStoreError):
            shared.store.add([Quad(ALICE, RDFS_LABEL, Literal("なりすまし"), graphs.DATA)])
        with pytest.raises(ReadOnlyStoreError):
            shared.store.update("CLEAR ALL")


def test_closing_a_shared_view_leaves_the_owner_usable(settings: Settings) -> None:
    with Runtime.create(settings) as runtime:
        shared = ReadOnlyGraph.sharing(runtime.store, runtime.search, settings)
        shared.close()
        assert runtime.store.count() == 0
        runtime.write(additions=[Quad(ALICE, RDFS_LABEL, Literal("x"), graphs.DATA)])
        assert runtime.store.count() == 1


@pytest.mark.anyio
async def test_the_shared_view_serves_the_same_read_only_tool_set(settings: Settings) -> None:
    with Runtime.create(settings) as runtime:
        shared = ReadOnlyGraph.sharing(runtime.store, runtime.search, settings)
        server = create_server(shared)
        names = {tool.name for tool in await server.list_tools()}
        assert len(names) == 10
        assert not any("insert" in name or "delete" in name for name in names)


def test_the_http_endpoint_is_mounted_and_read_only(settings: Settings) -> None:
    from ontoforge.api.app import create_app

    app = create_app(settings=settings)
    try:
        assert any(getattr(route, "path", "") == "/mcp" for route in app.routes)
        assert app.state.mcp_graph.store.read_only is True
    finally:
        app.state.runtime.close()
