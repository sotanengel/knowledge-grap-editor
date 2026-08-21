"""The MCP server: ten reference tools, four resources, three prompts (§9).

**Every tool here reads.** There is no write tool, no proposal queue and no
approval flow, because the graph's contents are a person's responsibility, not
an AI's (P4). Output defaults to Turtle, which is both cheaper in tokens and
easier for a language model to read than JSON-LD (§9.5).
"""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server import MCPServer
from pydantic import Field
from pyoxigraph import NamedNode, QueryBoolean, QuerySolutions, QueryTriples, Triple

from ontoforge import __version__
from ontoforge.config import Settings, load_settings
from ontoforge.io.graphview import local_name
from ontoforge.mcp.readonly import DEFAULT_LIMIT, ReadOnlyGraph
from ontoforge.mcp.rendering import (
    entity_lines,
    quads_to_turtle,
    solutions_to_table,
    triples_to_turtle,
)
from ontoforge.sparql.guard import SparqlRejectedError
from ontoforge.store import graphs

SERVER_NAME = "ontoforge"
INSTRUCTIONS = """\
OntoForge exposes a knowledge graph you can read but not change.

Start with `describe_ontology`: it tells you which classes exist, how many
instances each has and which properties connect them, so you can write a SPARQL
query against the real schema rather than a guessed one. Use `search_entities`
to find a starting node, `get_entity` and `get_neighbors` to explore around it,
and `sparql_select` when you need something specific.

Nothing you do here can modify the graph. If you have facts worth adding, use
the `extract_to_kg` prompt to write them as Turtle and hand them to the person
you are working with; they decide what goes in.\
"""

#: Cap on how much comes back from one call (§9.5).
RESULT_LIMIT = DEFAULT_LIMIT


class ToolError(RuntimeError):
    """Raised for a request that cannot be answered."""


def create_server(graph: ReadOnlyGraph, *, settings: Settings | None = None) -> MCPServer[Any]:
    """Build the MCP surface over an already-open read-only graph."""
    resolved = settings or graph.settings
    server: MCPServer[Any] = MCPServer(
        name=SERVER_NAME,
        title="OntoForge",
        version=__version__,
        instructions=INSTRUCTIONS,
    )

    def node(iri: str) -> NamedNode:
        try:
            return NamedNode(iri)
        except ValueError as error:
            raise ToolError(f"{iri!r} is not a valid IRI") from error

    # ------------------------------------------------------------------ tools

    @server.tool(description="Find nodes whose label or description matches a query.")
    def search_entities(
        query: Annotated[str, Field(description="Words to look for in labels and comments.")],
        type: Annotated[str | None, Field(description="Only nodes of this class IRI.")] = None,
        limit: Annotated[int, Field(ge=1, le=RESULT_LIMIT)] = 20,
    ) -> dict[str, Any]:
        found = graph.find(query, type_iri=type, limit=limit)
        return {"count": len(found), "entities": [entity.as_dict() for entity in found]}

    @server.tool(description="The full description of one node, as Turtle.")
    def get_entity(
        iri: Annotated[str, Field(description="The node's IRI.")],
        depth: Annotated[int, Field(ge=1, le=5, description="How far to follow relations.")] = 1,
    ) -> str:
        subject = node(iri)
        quads = graph.describe(subject, depth=depth)
        if not quads:
            raise ToolError(f"nothing is known about {iri}")
        return quads_to_turtle(graph, quads, heading=f"# {graph.label_for(subject)} <{iri}>")

    @server.tool(description="The class hierarchy, with instance counts.")
    def list_classes(
        root: Annotated[
            str | None, Field(description="Only this class and its subclasses.")
        ] = None,
    ) -> dict[str, Any]:
        classes = graph.classes()
        if root:
            wanted = _descendants(classes, root)
            classes = [entry for entry in classes if entry["iri"] in wanted]
        return {"count": len(classes), "classes": classes}

    @server.tool(description="Properties, with the classes they connect.")
    def list_properties(
        domain: Annotated[str | None, Field(description="Only properties of this class.")] = None,
    ) -> dict[str, Any]:
        found = graph.properties(domain=domain)
        return {"count": len(found), "properties": found}

    @server.tool(
        description=(
            "A plain-language summary of the whole graph: which classes exist, how many "
            "instances each has and which properties link them. Read this before writing "
            "a SPARQL query."
        )
    )
    def describe_ontology() -> str:
        return _summary(graph)

    @server.tool(description="The subgraph around one node.")
    def get_neighbors(
        iri: Annotated[str, Field(description="The node to start from.")],
        depth: Annotated[int, Field(ge=1, le=5)] = 1,
        max_nodes: Annotated[int, Field(ge=1, le=RESULT_LIMIT)] = 50,
    ) -> dict[str, Any]:
        entities, edges = graph.neighbours(node(iri), depth=depth, max_nodes=max_nodes)
        return {
            "nodes": [entity.as_dict() for entity in entities],
            "edges": edges,
            "truncated": len(entities) >= max_nodes,
        }

    @server.tool(description="The shortest chain of relations between two nodes.")
    def find_path(
        from_iri: Annotated[str, Field(description="Where to start.")],
        to_iri: Annotated[str, Field(description="Where to end.")],
        max_hops: Annotated[int, Field(ge=1, le=8)] = 5,
    ) -> dict[str, Any]:
        path = graph.shortest_path(node(from_iri), node(to_iri), max_hops=max_hops)
        if path is None:
            return {"found": False, "hops": 0, "path": []}
        return {"found": True, "hops": len(path), "path": path}

    @server.tool(
        description=(
            "Run a read-only SPARQL query (SELECT, ASK, CONSTRUCT or DESCRIBE). "
            "INSERT, DELETE, LOAD, CLEAR and DROP are refused before the query runs."
        )
    )
    def sparql_select(
        query: Annotated[str, Field(description="A SPARQL 1.1 query.")],
        limit: Annotated[int, Field(ge=1, le=RESULT_LIMIT)] = RESULT_LIMIT,
    ) -> dict[str, Any]:
        try:
            result = graph.query(query)
        except SparqlRejectedError as error:
            raise ToolError(f"refused: {error}") from error
        except (SyntaxError, ValueError) as error:
            raise ToolError(f"the query could not be parsed: {error}") from error

        if isinstance(result, QueryBoolean):
            return {"form": "ASK", "boolean": bool(result)}
        if isinstance(result, QueryTriples):
            triples: list[Triple] = []
            for triple in result:
                if len(triples) >= limit:
                    break
                triples.append(triple)
            return {
                "form": "CONSTRUCT",
                "count": len(triples),
                "turtle": triples_to_turtle(graph, triples),
            }
        if isinstance(result, QuerySolutions):
            return {"form": "SELECT", **solutions_to_table(graph, result, limit)}
        raise ToolError("the query returned something unexpected")  # pragma: no cover

    @server.tool(description="Check the graph against its SHACL shapes.")
    def validate_graph(
        shape: Annotated[str | None, Field(description="Only this shape's name.")] = None,
    ) -> dict[str, Any]:
        from ontoforge.mcp.validation_view import validate_read_only

        return validate_read_only(graph, shape_name=shape)

    @server.tool(
        description=(
            "Why a derived triple is in the graph: which rule produced it and from which premises."
        )
    )
    def explain_inference(
        subject: Annotated[str, Field(description="Subject IRI of the derived triple.")],
        predicate: Annotated[str, Field(description="Predicate IRI.")],
        object: Annotated[str, Field(description="Object IRI.")],
    ) -> dict[str, Any]:
        triple = Triple(node(subject), node(predicate), node(object))
        from ontoforge.mcp.inference_view import explain_read_only

        found = explain_read_only(graph, triple)
        if found is None:
            raise ToolError(
                "that triple was not derived by the reasoner; it is either asserted "
                "directly or not in the graph"
            )
        return found

    # ------------------------------------------------------------------ resources

    @server.resource(
        "ontoforge://ontology/schema.ttl",
        name="Ontology (Turtle)",
        mime_type="text/turtle",
        description="Every class and property definition, as Turtle.",
    )
    def schema_ttl() -> str:
        quads = list(graph.store.quads_for_pattern(None, None, None, graphs.ONTOLOGY))
        return quads_to_turtle(graph, quads, heading="# OntoForge ontology")

    @server.resource(
        "ontoforge://ontology/summary.md",
        name="Ontology summary",
        mime_type="text/markdown",
        description="The same information in prose, with instance counts.",
    )
    def summary_md() -> str:
        return _summary(graph)

    @server.resource(
        "ontoforge://graphs",
        name="Named graphs",
        mime_type="application/json",
        description="The named graphs and how much is in each.",
    )
    def graph_stats() -> dict[str, Any]:
        return graph.statistics()

    @server.resource(
        "ontoforge://examples/queries.md",
        name="Example queries",
        mime_type="text/markdown",
        description="SPARQL worked against this graph's own schema.",
    )
    def example_queries() -> str:
        return _examples(graph, resolved)

    # ------------------------------------------------------------------ prompts

    @server.prompt(description="A routine for exploring the graph from one node.")
    def explore_entity(iri: str) -> str:
        return (
            f"Explore the OntoForge knowledge graph starting from <{iri}>.\n\n"
            "1. Call `describe_ontology` first so you know what the schema looks like.\n"
            f"2. Call `get_entity` with iri={iri!r} to read what is asserted about it.\n"
            "3. Call `get_neighbors` to see what it connects to.\n"
            "4. Follow anything that looks relevant, and say when you are guessing.\n\n"
            "Report what the graph actually says. If something is missing, say it is "
            "missing rather than filling it in."
        )

    @server.prompt(description="Turn a question into SPARQL that fits this graph's schema.")
    def build_sparql(question: str) -> str:
        return (
            "Write a SPARQL query for the OntoForge knowledge graph that answers:\n\n"
            f"    {question}\n\n"
            "Before writing anything, call `describe_ontology` and `list_properties` so the "
            "query uses class and property IRIs that really exist. Then run it with "
            "`sparql_select` and check the result answers the question. If it comes back "
            "empty, say so and explain which assumption was wrong -- do not invent rows."
        )

    @server.prompt(
        description=(
            "Extract triples from a document as Turtle for a person to review. "
            "Nothing is written to the graph."
        )
    )
    def extract_to_kg(document: str) -> str:
        return (
            "Read the document below and propose triples for the OntoForge knowledge "
            "graph.\n\n"
            "First call `describe_ontology` so your triples use the vocabulary this graph "
            "already has, and only introduce a new term when nothing existing fits -- say so "
            "when you do.\n\n"
            "Output Turtle in a single fenced block, and nothing else that looks like "
            "Turtle. **You cannot write to the graph**: a person will read your output and "
            "paste it into the Turtle view if they agree with it. So mark anything you are "
            "unsure about with a comment rather than stating it flatly.\n\n"
            f"---\n\n{document}"
        )

    return server


# ---------------------------------------------------------------------- helpers


def _descendants(classes: list[dict[str, Any]], root: str) -> set[str]:
    """``root`` plus everything under it, following the recorded parents."""
    wanted = {root}
    changed = True
    while changed:
        changed = False
        for entry in classes:
            if entry["iri"] in wanted:
                continue
            if wanted.intersection(entry["parents"]):
                wanted.add(entry["iri"])
                changed = True
    return wanted


def _summary(graph: ReadOnlyGraph) -> str:
    """Schema first, in prose, so the model does not have to guess (§9.5)."""
    stats = graph.statistics()
    classes = graph.classes()
    properties = graph.properties()

    lines = [
        "# OntoForge knowledge graph",
        "",
        f"- base IRI: `{stats['baseIri']}`",
        f"- {stats['instances']} asserted statement(s) about instances",
        f"- {stats['ontology']} statement(s) of schema",
        f"- {stats['inferred']} derived statement(s) (reasoner: {stats['reasoner']})",
    ]
    if stats["vocabularies"]:
        lines.append(f"- external vocabularies loaded: {', '.join(stats['vocabularies'])}")

    lines += ["", "## Classes", ""]
    if classes:
        for entry in classes:
            parents = (
                f" (subclass of {', '.join(local_name(p) for p in entry['parents'])})"
                if entry["parents"]
                else ""
            )
            lines.append(
                f"- **{entry['label']}** `<{entry['iri']}>`{parents} "
                f"- {entry['instanceCount']} instance(s)"
            )
    else:
        lines.append("_No classes are defined yet._")

    lines += ["", "## Properties", ""]
    if properties:
        for entry in properties:
            domain = ", ".join(local_name(iri) for iri in entry["domain"]) or "anything"
            range_ = ", ".join(local_name(iri) for iri in entry["range"]) or "anything"
            lines.append(f"- **{entry['label']}** `<{entry['iri']}>`: {domain} → {range_}")
    else:
        lines.append("_No properties are defined yet._")

    lines += entity_lines(graph, classes)
    return "\n".join(lines)


def _examples(graph: ReadOnlyGraph, settings: Settings) -> str:
    """Example queries written against whatever schema is actually present."""
    classes = graph.classes()
    first = classes[0]["iri"] if classes else f"{settings.base_iri}ont#Person"
    properties = graph.properties()
    predicate = properties[0]["iri"] if properties else f"{settings.base_iri}ont#worksFor"

    return f"""\
# Example queries

All queries are read-only. Instance data lives in `<{graphs.DATA.value}>`, schema
in `<{graphs.ONTOLOGY.value}>` and anything the reasoner derived in
`<{graphs.INFERRED.value}>`.

## Everything of one class, with labels

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?item ?label WHERE {{
  GRAPH <{graphs.DATA.value}> {{
    ?item a <{first}> ;
          rdfs:label ?label .
  }}
}} LIMIT 50
```

## Follow one relation

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?fromLabel ?toLabel WHERE {{
  GRAPH <{graphs.DATA.value}> {{
    ?from <{predicate}> ?to ;
          rdfs:label ?fromLabel .
    ?to rdfs:label ?toLabel .
  }}
}} LIMIT 50
```

## Include what the reasoner worked out

```sparql
SELECT ?item WHERE {{
  {{ GRAPH <{graphs.DATA.value}> {{ ?item a <{first}> }} }}
  UNION
  {{ GRAPH <{graphs.INFERRED.value}> {{ ?item a <{first}> }} }}
}} LIMIT 50
```

## How many instances of each class

```sparql
SELECT ?class (COUNT(?item) AS ?count) WHERE {{
  GRAPH <{graphs.DATA.value}> {{ ?item a ?class }}
}} GROUP BY ?class ORDER BY DESC(?count)
```
"""


def build_from_settings(settings: Settings | None = None) -> tuple[MCPServer[Any], ReadOnlyGraph]:
    """Open the store read-only and wrap it in the MCP surface."""
    resolved = settings or load_settings()
    graph = ReadOnlyGraph.open(resolved)
    return create_server(graph, settings=resolved), graph


def run_stdio(settings: Settings | None = None) -> None:  # pragma: no cover - process entry
    """``docker run -i --rm -v ./data:/data ontoforge mcp-stdio`` (§9.1)."""
    server, graph = build_from_settings(settings)
    try:
        server.run(transport="stdio")
    finally:
        graph.close()


__all__ = ["ToolError", "build_from_settings", "create_server", "run_stdio"]
