import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, Edge, Node } from "../api/client";
import GraphCanvas from "../features/graph/GraphCanvas";
import Inspector from "../features/inspector/Inspector";
import LeftNavigator from "../features/navigator/LeftNavigator";
import ThreeColumnLayout from "../layout/ThreeColumnLayout";
import StatusBar from "../layout/StatusBar";

export default function GraphPage() {
  const [searchParams] = useSearchParams();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [searchQuery, setSearchQuery] = useState(searchParams.get("q") || "");
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
    const q = searchParams.get("q") || "";
    setSearchQuery(q);
    loadGraph(q || undefined);
  }, [searchParams, loadGraph]);

  const handleSearch = () => {
    loadGraph(searchQuery || undefined);
  };

  const isEmpty = nodes.length === 0 && edges.length === 0 && !status;

  return (
    <>
      <ThreeColumnLayout
        left={
          <LeftNavigator
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onSearch={handleSearch}
            depth={depth}
            onDepthChange={setDepth}
          />
        }
        center={
          <div className="graph-area">
            <GraphCanvas nodes={nodes} edges={edges} />
            {isEmpty && (
              <div className="empty-state-overlay" data-testid="empty-state">
                <p>まだナレッジグラフがありません</p>
                <p>Nodeを追加してグラフを構築してください。</p>
                <div className="btn-row">
                  <button type="button">Nodeを追加</button>
                  <Link to="/ontology" className="btn-link">
                    Ontologyを見る
                  </Link>
                </div>
              </div>
            )}
            {status && (
              <div className="error-panel">
                <p className="error">{status}</p>
                <button type="button" onClick={() => loadGraph(searchQuery || undefined)}>
                  再試行
                </button>
              </div>
            )}
          </div>
        }
        right={<Inspector />}
      />
      <StatusBar nodeCount={nodes.length} edgeCount={edges.length} />
    </>
  );
}
