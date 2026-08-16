import { useCallback, useEffect, useState } from "react";
import { api, Edge, Node } from "./api/client";
import EdgeEditor from "./components/EdgeEditor";
import GraphCanvas from "./components/GraphCanvas";
import NodeEditor from "./components/NodeEditor";
import OntologyPanel from "./components/OntologyPanel";

type EditorMode = "none" | "node" | "edge" | "create-node" | "create-edge";

export default function App() {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<Edge | null>(null);
  const [editorMode, setEditorMode] = useState<EditorMode>("none");
  const [depth, setDepth] = useState(1);
  const [status, setStatus] = useState("");

  const loadGraph = useCallback(async (query?: string) => {
    try {
      if (query) {
        const result = await api.searchGraph(query);
        setNodes(result.nodes);
        setEdges(result.edges);
      } else {
        const [n, e] = await Promise.all([api.listNodes(), api.listEdges()]);
        setNodes(n);
        setEdges(e);
      }
      setStatus("");
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "読み込みに失敗しました");
    }
  }, []);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const handleSearch = () => {
    loadGraph(searchQuery || undefined);
  };

  const handleNodeSelect = async (node: Node) => {
    setSelectedNode(node);
    setSelectedEdge(null);
    setEditorMode("node");
    try {
      const neighbors = await api.getNeighbors(node.id, depth);
      setNodes(neighbors.nodes);
      setEdges(neighbors.edges);
    } catch {
      /* keep current graph */
    }
  };

  const handleExport = async (format: string) => {
    const blob = await api.exportRdf(format);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `knowledge-graph.${format === "jsonld" ? "jsonld" : format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app">
      <header>
        <h1>ナレッジグラフ</h1>
        <div className="header-actions">
          <select
            value=""
            onChange={(e) => e.target.value && handleExport(e.target.value)}
            aria-label="Export形式"
          >
            <option value="">Export...</option>
            <option value="turtle">Turtle</option>
            <option value="nt">N-Triples</option>
            <option value="jsonld">JSON-LD</option>
            <option value="xml">RDF/XML</option>
          </select>
        </div>
      </header>
      <div className="layout">
        <aside className="sidebar">
          <section>
            <h3>検索</h3>
            <div className="search-row">
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="ノードを検索..."
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              />
              <button type="button" onClick={handleSearch}>検索</button>
            </div>
            <label>
              探索深度
              <input
                type="number"
                min={1}
                max={5}
                value={depth}
                onChange={(e) => setDepth(Number(e.target.value))}
              />
            </label>
          </section>
          <OntologyPanel onChange={() => loadGraph()} />
          <section>
            <h3>ノード一覧</h3>
            <ul className="node-list">
              {nodes.map((n) => (
                <li key={n.id} onClick={() => handleNodeSelect(n)}>
                  <strong>{n.label}</strong>
                  <span>{n.type}</span>
                </li>
              ))}
            </ul>
          </section>
          <div className="btn-row">
            <button type="button" onClick={() => { setEditorMode("create-node"); setSelectedNode(null); }}>
              + ノード
            </button>
            <button type="button" onClick={() => { setEditorMode("create-edge"); setSelectedEdge(null); }}>
              + エッジ
            </button>
            <button type="button" onClick={() => loadGraph()}>全件表示</button>
          </div>
          {(editorMode === "node" || editorMode === "create-node") && (
            <NodeEditor
              node={editorMode === "node" ? selectedNode : null}
              onSave={() => { setEditorMode("none"); loadGraph(); }}
              onDelete={() => { setSelectedNode(null); setEditorMode("none"); }}
            />
          )}
          {(editorMode === "edge" || editorMode === "create-edge") && (
            <EdgeEditor
              edge={editorMode === "edge" ? selectedEdge : null}
              nodes={nodes}
              onSave={() => { setEditorMode("none"); loadGraph(); }}
              onDelete={() => { setSelectedEdge(null); setEditorMode("none"); }}
            />
          )}
          {status && <p className="error">{status}</p>}
        </aside>
        <main className="graph-area">
          <GraphCanvas
            nodes={nodes}
            edges={edges}
            onNodeSelect={handleNodeSelect}
            onEdgeSelect={(edge) => {
              setSelectedEdge(edge);
              setEditorMode("edge");
            }}
          />
        </main>
      </div>
    </div>
  );
}
