from __future__ import annotations

from datetime import datetime

from app.config import settings
from app.models.schemas import (
    Edge,
    EdgeCreate,
    EdgeUpdate,
    GraphSearchResult,
    Metadata,
    NeighborResult,
    Node,
    NodeCreate,
    NodeUpdate,
)
from app.ontology.abox.service import ABoxService
from app.ontology.inference.service import InferenceService
from app.storage import rdf_constants as R
from app.storage.oxigraph_store import OxigraphStore


class GraphService:
    def __init__(self, store: OxigraphStore) -> None:
        self.store = store
        self.graph = store.data_graph
        self.abox = ABoxService(store)
        self.inference = InferenceService(store)

    def _parse_metadata(self, rows: list[dict[str, str]], uri: str) -> Metadata:
        created = None
        updated = None
        for row in rows:
            if row.get("s") != uri:
                continue
            p = row.get("p", "")
            val = row.get("o", "")
            if p == R.KG_CREATED_AT:
                created = datetime.fromisoformat(val)
            elif p == R.KG_UPDATED_AT:
                updated = datetime.fromisoformat(val)
        return Metadata(created_at=created, updated_at=updated)

    def list_nodes(self, type_filter: str | None = None) -> list[Node]:
        if type_filter:
            sparql = f"""
            PREFIX rdfs: <{R.RDFS}>
            SELECT ?s ?label ?type ?p ?o WHERE {{
              GRAPH <{settings.data_graph}> {{
                ?s a <{R.class_uri(type_filter)}> ;
                   rdfs:label ?label ;
                   <{R.RDF_TYPE}> ?type .
                OPTIONAL {{ ?s ?p ?o . FILTER(isLiteral(?o)) }}
              }}
            }}
            """
        else:
            sparql = f"""
            PREFIX rdfs: <{R.RDFS}>
            SELECT ?s ?label ?type ?p ?o WHERE {{
              GRAPH <{settings.data_graph}> {{
                ?s a ?type ;
                   rdfs:label ?label .
                FILTER(STRSTARTS(STR(?s), "{R.KG}node:"))
                OPTIONAL {{ ?s ?p ?o . FILTER(isLiteral(?o)) }}
              }}
            }}
            """
        rows = self.store.query(sparql)
        return self._aggregate_nodes(rows)

    def _aggregate_nodes(self, rows: list[dict[str, str]]) -> list[Node]:
        nodes: dict[str, Node] = {}
        for row in rows:
            uri = row["s"]
            node_id = R.local_name(uri)
            if node_id not in nodes:
                type_uri = row.get("type", "")
                nodes[node_id] = Node(
                    id=node_id,
                    label=row.get("label", node_id),
                    type=R.class_id_from_uri(type_uri) if type_uri else "",
                    properties={},
                )
            p = row.get("p")
            o = row.get("o")
            if p and o and p not in (R.RDFS_LABEL, R.RDF_TYPE, R.KG_CREATED_AT, R.KG_UPDATED_AT):
                prop_name = R.local_name(p)
                if prop_name.startswith("property:"):
                    prop_name = prop_name.split(":", 1)[1]
                nodes[node_id].properties[prop_name] = o
        return list(nodes.values())

    def get_node(self, node_id: str) -> Node | None:
        uri = R.node_uri(node_id)
        sparql = f"""
        PREFIX rdfs: <{R.RDFS}>
        SELECT ?label ?type ?p ?o ?created ?updated WHERE {{
          GRAPH <{settings.data_graph}> {{
            <{uri}> a ?type ;
                    rdfs:label ?label .
            OPTIONAL {{ <{uri}> ?p ?o . FILTER(isLiteral(?o)) }}
            OPTIONAL {{ <{uri}> <{R.KG_CREATED_AT}> ?created }}
            OPTIONAL {{ <{uri}> <{R.KG_UPDATED_AT}> ?updated }}
          }}
        }}
        """
        rows = self.store.query(sparql)
        if not rows:
            return None
        row = rows[0]
        node = Node(
            id=node_id,
            label=row.get("label", node_id),
            type=R.class_id_from_uri(row.get("type", "")),
            properties={},
            metadata=Metadata(
                created_at=datetime.fromisoformat(row["created"]) if row.get("created") else None,
                updated_at=datetime.fromisoformat(row["updated"]) if row.get("updated") else None,
            ),
        )
        for r in rows:
            p = r.get("p")
            o = r.get("o")
            if p and o and p not in (R.RDFS_LABEL, R.RDF_TYPE, R.KG_CREATED_AT, R.KG_UPDATED_AT):
                prop_name = R.local_name(p)
                if prop_name.startswith("property:"):
                    prop_name = prop_name.split(":", 1)[1]
                node.properties[prop_name] = o
        return node

    def create_node(self, data: NodeCreate) -> Node:
        uri = R.node_uri(data.id)
        now = self.store.now_literal()
        self.store.add_quad(uri, R.RDF_TYPE, R.class_uri(data.type), self.graph)
        self.store.add_quad(uri, R.RDFS_LABEL, self.store.literal(data.label), self.graph)
        self.store.add_quad(uri, R.KG_CREATED_AT, now, self.graph)
        self.store.add_quad(uri, R.KG_UPDATED_AT, now, self.graph)
        for key, value in data.properties.items():
            self.abox.add_datatype_assertion(data.id, key, value)
        self.inference.apply_inferred()
        return self.get_node(data.id) or Node(id=data.id, label=data.label, type=data.type)

    def update_node(self, node_id: str, data: NodeUpdate) -> Node | None:
        existing = self.get_node(node_id)
        if not existing:
            return None
        uri = R.node_uri(node_id)
        self.store.remove_entity_quads(uri, self.graph)
        label = data.label if data.label is not None else existing.label
        node_type = data.type if data.type is not None else existing.type
        properties = data.properties if data.properties is not None else existing.properties
        now = self.store.now_literal()
        created = (
            self.store.literal(existing.metadata.created_at.isoformat())
            if existing.metadata.created_at
            else now
        )
        self.store.add_quad(uri, R.RDF_TYPE, R.class_uri(node_type), self.graph)
        self.store.add_quad(uri, R.RDFS_LABEL, self.store.literal(label), self.graph)
        self.store.add_quad(uri, R.KG_CREATED_AT, created, self.graph)
        self.store.add_quad(uri, R.KG_UPDATED_AT, now, self.graph)
        for key, value in properties.items():
            self.abox.add_datatype_assertion(node_id, key, value)
        self.inference.apply_inferred()
        return self.get_node(node_id)

    def delete_node(self, node_id: str) -> bool:
        uri = R.node_uri(node_id)
        existing = self.get_node(node_id)
        if not existing:
            return False
        # Cascade delete edges
        for edge in self.list_edges():
            if edge.subject == node_id or edge.object == node_id:
                self.delete_edge(edge.id)
        self.store.remove_entity_quads(uri, self.graph)
        return True

    def list_edges(self) -> list[Edge]:
        sparql = f"""
        PREFIX rdfs: <{R.RDFS}>
        PREFIX kg: <{R.KG}>
        SELECT ?edge ?subject ?predicate ?object ?created ?updated WHERE {{
          GRAPH <{settings.data_graph}> {{
            ?edge <{R.KG_EDGE_ID}> ?edgeId ;
                  a kg:Edge ;
                  kg:subject ?subject ;
                  kg:predicate ?predicate ;
                  kg:object ?object .
            OPTIONAL {{ ?edge <{R.KG_CREATED_AT}> ?created }}
            OPTIONAL {{ ?edge <{R.KG_UPDATED_AT}> ?updated }}
          }}
        }}
        """
        rows = self.store.query(sparql)
        edges: list[Edge] = []
        for row in rows:
            edges.append(
                Edge(
                    id=R.local_name(row.get("edge", "")),
                    subject=R.local_name(row["subject"]),
                    predicate=R.local_name(row["predicate"]).replace("relationship:", ""),
                    object=R.local_name(row["object"]),
                    metadata=Metadata(
                        created_at=datetime.fromisoformat(row["created"])
                        if row.get("created")
                        else None,
                        updated_at=datetime.fromisoformat(row["updated"])
                        if row.get("updated")
                        else None,
                    ),
                )
            )
        return edges

    def get_edge(self, edge_id: str) -> Edge | None:
        for edge in self.list_edges():
            if edge.id == edge_id:
                return edge
        return None

    def create_edge(self, data: EdgeCreate) -> Edge:
        edge_uri = R.edge_uri(data.id)
        now = self.store.now_literal()
        subj_uri = R.node_uri(data.subject)
        obj_uri = R.node_uri(data.object)
        pred_uri = R.relationship_uri(data.predicate)
        self.store.add_quad(edge_uri, R.RDF_TYPE, f"{R.KG}Edge", self.graph)
        self.store.add_quad(edge_uri, R.KG_EDGE_ID, self.store.literal(data.id), self.graph)
        self.store.add_quad(edge_uri, f"{R.KG}subject", subj_uri, self.graph)
        self.store.add_quad(edge_uri, f"{R.KG}predicate", pred_uri, self.graph)
        self.store.add_quad(edge_uri, f"{R.KG}object", obj_uri, self.graph)
        self.store.add_quad(edge_uri, R.KG_CREATED_AT, now, self.graph)
        self.store.add_quad(edge_uri, R.KG_UPDATED_AT, now, self.graph)
        # Also store as direct triple for graph traversal
        self.store.add_quad(subj_uri, pred_uri, obj_uri, self.graph)
        self.inference.apply_inferred()
        return self.get_edge(data.id) or Edge(
            id=data.id,
            subject=data.subject,
            predicate=data.predicate,
            object=data.object,
        )

    def update_edge(self, edge_id: str, data: EdgeUpdate) -> Edge | None:
        existing = self.get_edge(edge_id)
        if not existing:
            return None
        self.delete_edge(edge_id, remove_triple_only=False)
        updated = EdgeCreate(
            id=edge_id,
            subject=data.subject or existing.subject,
            predicate=data.predicate or existing.predicate,
            object=data.object or existing.object,
            properties=data.properties or existing.properties,
        )
        return self.create_edge(updated)

    def delete_edge(self, edge_id: str, remove_triple_only: bool = False) -> bool:
        existing = self.get_edge(edge_id)
        if not existing:
            return False
        subj_uri = R.node_uri(existing.subject)
        pred_uri = R.relationship_uri(existing.predicate)
        obj_uri = R.node_uri(existing.object)
        edge_uri = R.edge_uri(edge_id)
        # Remove direct triple
        from pyoxigraph import Quad

        s = self.store._named_node(subj_uri)
        p = self.store._named_node(pred_uri)
        o = self.store._named_node(obj_uri)
        try:
            self.store.store.remove(Quad(s, p, o, self.graph))
        except Exception:
            pass
        self.store.remove_entity_quads(edge_uri, self.graph)
        return True

    def search(self, query: str) -> GraphSearchResult:
        q = query.lower().replace('"', "")
        sparql = f"""
        PREFIX rdfs: <{R.RDFS}>
        SELECT DISTINCT ?s ?label ?type WHERE {{
          GRAPH <{settings.data_graph}> {{
            ?s a ?type ;
               rdfs:label ?label .
            FILTER(STRSTARTS(STR(?s), "{R.KG}node:"))
            FILTER(CONTAINS(LCASE(STR(?label)), "{q}") ||
                   CONTAINS(LCASE(STR(?s)), "{q}"))
          }}
        }}
        """
        rows = self.store.query(sparql)
        node_ids = {R.local_name(r["s"]) for r in rows}
        nodes = [n for n in self.list_nodes() if n.id in node_ids]
        edges = [e for e in self.list_edges() if e.subject in node_ids or e.object in node_ids]
        return GraphSearchResult(nodes=nodes, edges=edges)

    def get_neighbors(self, node_id: str, depth: int = 1) -> NeighborResult | None:
        center = self.get_node(node_id)
        if not center:
            return None
        visited_nodes: set[str] = {node_id}
        visited_edges: set[str] = set()
        frontier = {node_id}
        all_nodes: dict[str, Node] = {node_id: center}
        all_edges: list[Edge] = []

        for _ in range(depth):
            next_frontier: set[str] = set()
            for e in self.list_edges():
                if e.id in visited_edges:
                    continue
                if e.subject in frontier or e.object in frontier:
                    visited_edges.add(e.id)
                    all_edges.append(e)
                    for nid in (e.subject, e.object):
                        if nid not in visited_nodes:
                            visited_nodes.add(nid)
                            next_frontier.add(nid)
                            node = self.get_node(nid)
                            if node:
                                all_nodes[nid] = node
            frontier = next_frontier

        return NeighborResult(
            center=center,
            nodes=list(all_nodes.values()),
            edges=all_edges,
            depth=depth,
        )

    def find_relationship_path(
        self, source: str, target: str, max_depth: int = 4
    ) -> list[dict[str, str]]:
        """Find paths between two nodes by label or id."""
        sparql = f"""
        SELECT ?path WHERE {{
          GRAPH <{settings.data_graph}> {{
            {{
              SELECT ?s ?label WHERE {{
                ?s <{R.RDFS_LABEL}> ?label .
                FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{source}")) ||
                       CONTAINS(LCASE(STR(?s)), LCASE("{source}")))
              }}
            }}
            {{
              SELECT ?t ?tlabel WHERE {{
                ?t <{R.RDFS_LABEL}> ?tlabel .
                FILTER(CONTAINS(LCASE(STR(?tlabel)), LCASE("{target}")) ||
                       CONTAINS(LCASE(STR(?t)), LCASE("{target}")))
              }}
            }}
          }}
        }}
        """
        _ = sparql
        # BFS over edges for MVP
        source_nodes = [
            n for n in self.list_nodes() if source.lower() in n.label.lower() or source == n.id
        ]
        target_nodes = [
            n for n in self.list_nodes() if target.lower() in n.label.lower() or target == n.id
        ]
        paths: list[dict[str, str]] = []
        for sn in source_nodes:
            for tn in target_nodes:
                if sn.id == tn.id:
                    paths.append({"source": sn.id, "target": tn.id, "path": sn.id})
                    continue
                for e in self.list_edges():
                    if (e.subject == sn.id and e.object == tn.id) or (
                        e.subject == tn.id and e.object == sn.id
                    ):
                        paths.append(
                            {
                                "source": sn.id,
                                "target": tn.id,
                                "relationship": e.predicate,
                                "path": f"{sn.id} --{e.predicate}--> {tn.id}",
                            }
                        )
        return paths
