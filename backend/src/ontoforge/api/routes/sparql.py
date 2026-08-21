"""SPARQL 1.1 Protocol endpoints (§8).

``/sparql`` answers queries and refuses anything that could change the graph.
``/sparql/update`` writes, and is deliberately a separate route: the MCP server
mounts only read-only tools and opens the store read-only, so it has no path
here at all (§9, §13).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from pyoxigraph import Quad, QueryBoolean, QuerySolutions, QueryTriples, RdfFormat, serialize

from ontoforge.api.deps import RuntimeDep
from ontoforge.literals import term_to_json
from ontoforge.namespaces import PREFIXES
from ontoforge.runtime import Runtime
from ontoforge.sparql.guard import SparqlRejectedError, ensure_read_only
from ontoforge.store import graphs

router = APIRouter(tags=["sparql"])

SPARQL_JSON = "application/sparql-results+json"
TURTLE = "text/turtle"
UPDATE_ACTOR = "sparql-update"

#: A single result page never exceeds this, whatever the query asks for (§9.5).
MAX_RESULTS = 10_000


async def _query_text(request: Request, query: str | None) -> str:
    """A query may arrive as ?query=, as a form field, or as a raw body."""
    if query:
        return query
    body = (await request.body()).decode("utf-8").strip()
    if not body:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no query was supplied")
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/x-www-form-urlencoded"):
        form = await request.form()
        value = form.get("query") or form.get("update")
        if isinstance(value, str):
            return value
    return body


def _solutions_json(solutions: QuerySolutions, limit: int) -> dict[str, Any]:
    variables = [str(variable)[1:] for variable in solutions.variables]
    bindings: list[dict[str, Any]] = []
    for solution in solutions:
        if len(bindings) >= limit:
            break
        row: dict[str, Any] = {}
        for name in variables:
            term = solution[name]
            if term is not None:
                row[name] = _binding(term)
        bindings.append(row)
    return {"head": {"vars": variables}, "results": {"bindings": bindings}}


def _binding(term: Any) -> dict[str, Any]:
    """SPARQL results JSON shape, derived from the JSON-LD shape."""
    payload = term_to_json(term)
    if "@id" in payload:
        iri: str = payload["@id"]
        if iri.startswith("_:"):
            return {"type": "bnode", "value": iri.removeprefix("_:")}
        return {"type": "uri", "value": iri}
    binding: dict[str, Any] = {"type": "literal", "value": payload.get("@value", "")}
    if "@language" in payload:
        binding["xml:lang"] = payload["@language"]
    elif "@type" in payload:
        binding["datatype"] = payload["@type"]
    return binding


def _run(runtime: Runtime, query: str) -> Response:
    try:
        form = ensure_read_only(query)
    except SparqlRejectedError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    try:
        result = runtime.store.query(query)
    except (SyntaxError, ValueError) as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid query: {error}") from error

    if isinstance(result, QueryBoolean):
        return Response(
            content=f'{{"head": {{}}, "boolean": {str(bool(result)).lower()}}}',
            media_type=SPARQL_JSON,
        )
    if isinstance(result, QueryTriples):
        quads = [Quad(t.subject, t.predicate, t.object) for t in result]
        payload = serialize(quads, format=RdfFormat.TURTLE, prefixes=dict(PREFIXES))
        return Response(content=payload, media_type=TURTLE)
    if isinstance(result, QuerySolutions):
        import json

        return Response(
            content=json.dumps(_solutions_json(result, MAX_RESULTS), ensure_ascii=False),
            media_type=SPARQL_JSON,
        )
    raise HTTPException(  # pragma: no cover - the four forms are exhaustive
        status.HTTP_400_BAD_REQUEST, f"unsupported query form {form}"
    )


@router.get("/sparql")
async def sparql_get(request: Request, runtime: RuntimeDep, query: str = "") -> Response:
    return _run(runtime, await _query_text(request, query))


@router.post("/sparql")
async def sparql_post(request: Request, runtime: RuntimeDep, query: str = "") -> Response:
    return _run(runtime, await _query_text(request, query))


@router.post("/sparql/update")
async def sparql_update(
    request: Request,
    runtime: RuntimeDep,
    update: Annotated[str, ""] = "",
) -> dict[str, Any]:
    """Apply a SPARQL Update, recording the resulting change (§6.4)."""
    text = await _query_text(request, update or None)

    try:
        ensure_read_only(text)
    except SparqlRejectedError:
        pass  # An update is exactly what this endpoint is for.
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "this endpoint takes SPARQL Update; send queries to /sparql",
        )

    before = _snapshot(runtime)
    try:
        runtime.store.update(text)
    except (SyntaxError, ValueError) as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid update: {error}") from error
    after = _snapshot(runtime)

    # The store applied the change directly, so the log is reconciled against a
    # before/after diff rather than a set of quads handed in up front.
    additions = after - before
    deletions = before - after
    patch = runtime.changelog.record(additions=additions, deletions=deletions, actor=UPDATE_ACTOR)
    if patch is not None:
        runtime.after_external_write(patch)
    return {
        "additions": len(additions),
        "deletions": len(deletions),
        "seq": patch.seq if patch else runtime.changelog.last_seq,
    }


def _snapshot(runtime: Runtime) -> set[Quad]:
    """Every quad in the graphs a SPARQL Update is allowed to touch."""
    return {
        quad
        for graph in (*graphs.USER_EDITABLE, graphs.INFERRED, graphs.LAYOUT)
        for quad in runtime.store.quads_for_pattern(None, None, None, graph)
    }
