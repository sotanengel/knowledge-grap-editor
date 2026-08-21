#!/usr/bin/env bash
# Phase 1 acceptance (§14): from an empty store, build a 50-node knowledge
# graph, export it as Turtle, and read it back through MCP -- while confirming
# that MCP cannot write.
set -euo pipefail

BASE="${ONTOFORGE_BASE_URL:-http://127.0.0.1:8080}"
NODES="${ONTOFORGE_E2E_NODES:-50}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

say() { printf '\n=== %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

say "waiting for $BASE to answer (NFR-02: within 10 seconds)"
START=$(date +%s)
for _ in $(seq 1 100); do
  if curl -sf "$BASE/api/v1/health" >/dev/null 2>&1; then break; fi
  sleep 0.1
done
curl -sf "$BASE/api/v1/health" >/dev/null || fail "the server never became ready"
printf 'ready after %s second(s)\n' "$(( $(date +%s) - START ))"

say "defining the vocabulary"
curl -sf -X POST "$BASE/api/v1/ontology/classes" \
  -H 'Content-Type: application/json' -d '{"label":"人物"}' >/dev/null
curl -sf -X POST "$BASE/api/v1/ontology/classes" \
  -H 'Content-Type: application/json' -d '{"label":"組織"}' >/dev/null
# 社員 is a 人物, so the reasoner has something real to derive.
curl -sf -X POST "$BASE/api/v1/ontology/classes" \
  -H 'Content-Type: application/json' -d '{"label":"社員","parents":["ont:人物"]}' >/dev/null
curl -sf -X POST "$BASE/api/v1/ontology/properties" \
  -H 'Content-Type: application/json' \
  -d '{"label":"所属","domain":"ont:人物","range":"ont:組織"}' >/dev/null

say "creating an organisation and $((NODES - 1)) people"
ACME=$(curl -sf -X POST "$BASE/api/v1/entities" -H 'Content-Type: application/json' \
  -d '{"label":"株式会社アクメ","types":["ont:組織"]}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["@id"])')

for i in $(seq 1 $((NODES - 1))); do
  curl -sf -X POST "$BASE/api/v1/entities" -H 'Content-Type: application/json' \
    -d "{\"label\":\"社員${i}\",\"types\":[\"ont:社員\"],\"properties\":{\"ont:所属\":{\"@id\":\"${ACME}\"}}}" \
    >/dev/null
done

COUNT=$(curl -sf "$BASE/api/v1/entities?limit=500" \
  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["@graph"]))')
[ "$COUNT" -ge "$NODES" ] || fail "expected at least $NODES nodes, found $COUNT"
printf '%s node(s) in the graph\n' "$COUNT"

say "exporting Turtle"
curl -sf "$BASE/api/v1/export?format=turtle" -o "$WORK/graph.ttl"
grep -q '株式会社アクメ' "$WORK/graph.ttl" || fail "the export is missing its content"
printf 'exported %s byte(s)\n' "$(wc -c < "$WORK/graph.ttl")"

say "running the reasoner"
DERIVED=$(curl -sf -X POST "$BASE/api/v1/reason" -H 'Content-Type: application/json' -d '{}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["derived"])')
[ "$DERIVED" -gt 0 ] || fail "the reasoner derived nothing from a subclass hierarchy"
printf 'derived %s triple(s)\n' "$DERIVED"

say "reading through MCP: search_entities"
python3 - "$BASE" "$ACME" <<'PY'
import json, sys, urllib.request

base, acme = sys.argv[1], sys.argv[2]
session = {"id": None}

# The endpoint is mounted at /mcp, which Starlette redirects to /mcp/. Real MCP
# clients follow that; urllib refuses to redirect a POST unless told to.
class KeepMethod(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return urllib.request.Request(
            newurl, data=req.data, headers=dict(req.header_items()), method=req.get_method()
        )


opener = urllib.request.build_opener(KeepMethod)


def rpc(method, params=None, notify=False):
    body = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        body["params"] = params
    if not notify:
        body["id"] = 1
    request = urllib.request.Request(
        f"{base}/mcp",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **({"Mcp-Session-Id": session["id"]} if session["id"] else {}),
        },
        method="POST",
    )
    with opener.open(request, timeout=15) as response:
        if session["id"] is None:
            session["id"] = response.headers.get("Mcp-Session-Id")
        raw = response.read().decode()
    if notify:
        return None
    for line in raw.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return json.loads(raw) if raw.strip() else None


rpc("initialize", {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "e2e", "version": "0"},
})
rpc("notifications/initialized", {}, notify=True)

tools = {tool["name"] for tool in rpc("tools/list", {})["result"]["tools"]}
assert tools, "MCP published no tools"
forbidden = {name for name in tools if any(w in name for w in ("insert", "delete", "update", "create", "write"))}
assert not forbidden, f"MCP published a write tool: {forbidden}"
print(f"{len(tools)} read-only tool(s):", ", ".join(sorted(tools)))

found = rpc("tools/call", {"name": "search_entities", "arguments": {"query": "社員"}})
hits = found["result"]["structuredContent"]["count"]
assert hits > 0, "search_entities found nothing"
print(f"search_entities returned {hits} hit(s)")

selected = rpc("tools/call", {
    "name": "sparql_select",
    "arguments": {"query": "SELECT ?s WHERE { GRAPH ?g { ?s ?p ?o } } LIMIT 5"},
})
rows = selected["result"]["structuredContent"]["count"]
assert rows > 0, "sparql_select returned nothing"
print(f"sparql_select returned {rows} row(s)")

refused = rpc("tools/call", {
    "name": "sparql_select",
    "arguments": {"query": "INSERT DATA { <https://a> <https://b> <https://c> }"},
})
assert refused["result"].get("isError"), "MCP accepted a SPARQL Update"
print("sparql_select refused INSERT DATA, as it must (FR-16)")
PY

say "confirming the graph is unchanged"
AFTER=$(curl -sf "$BASE/api/v1/entities?limit=500" \
  | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["@graph"]))')
[ "$AFTER" = "$COUNT" ] || fail "the node count changed after the MCP calls"

printf '\nPhase 1 acceptance passed.\n'
