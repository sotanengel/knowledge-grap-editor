import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, Edge, Node } from "../api/client";
import GraphCanvas, { type GraphCanvasHandle } from "../features/graph/GraphCanvas";
import { useGraphState } from "../features/graph/useGraphState";
import Inspector, { type InspectorMode } from "../features/inspector/Inspector";
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
  const [inspectorMode, setInspectorMode] = useState<InspectorMode>("empty");
  const canvasRef = useRef<GraphCanvasHandle>(null);
  const {
    selectedNode,
    selectedEdge,
    selectNode,
    selectEdge,
    clearSelection,
    zoom,
    setZoom,
    selectionLabel,
  } = useGraphState();

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
      setStatus(e instanceof Error ? e.message : "データを取得できませんでした");
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

  const handleNodeSelect = useCallback(
    async (node: Node) => {
      setInspectorMode("node");
      selectNode(node);
      try {
        const neighbors = await api.getNeighbors(node.id, depth);
        setNodes(neighbors.nodes);
        setEdges(neighbors.edges);
      } catch {
        /* keep current graph */
      }
    },
    [depth, selectNode],
  );

  const handleEdgeSelect = useCallback(
    (edge: Edge) => {
      setInspectorMode("edge");
      selectEdge(edge);
    },
    [selectEdge],
  );

  const handleNodeExpand = useCallback(
    async (node: Node) => {
      setInspectorMode("node");
      selectNode(node);
      try {
        const neighbors = await api.getNeighbors(node.id, depth);
        setNodes(neighbors.nodes);
        setEdges(neighbors.edges);
      } catch {
        /* keep current graph */
      }
    },
    [depth, selectNode],
  );

  const handleAddNode = () => {
    clearSelection();
    setInspectorMode("create-node");
  };

  const handleAddRelationship = () => {
    setInspectorMode("create-edge");
  };

  const handleClearSelection = () => {
    clearSelection();
    setInspectorMode("empty");
  };

  useEffect(() => {
    const timer = setInterval(() => {
      if (canvasRef.current) {
        setZoom(canvasRef.current.getZoom());
      }
    }, 500);
    return () => clearInterval(timer);
  }, [setZoom]);

  const isEmpty = nodes.length === 0 && edges.length === 0 && !status;

  const resolvedMode: InspectorMode =
    inspectorMode === "create-node" || inspectorMode === "create-edge"
      ? inspectorMode
      : selectedNode
        ? "node"
        : selectedEdge
          ? "edge"
          : "empty";

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
            onAddNode={handleAddNode}
            onAddRelationship={handleAddRelationship}
          />
        }
        center={
          <div className="graph-area">
            <GraphCanvas
              ref={canvasRef}
              nodes={nodes}
              edges={edges}
              onNodeSelect={handleNodeSelect}
              onEdgeSelect={handleEdgeSelect}
              onNodeExpand={handleNodeExpand}
              onBackgroundClick={handleClearSelection}
              selectedNodeId={selectedNode?.id ?? null}
              selectedEdgeId={selectedEdge?.id ?? null}
            />
            {isEmpty && (
              <div className="empty-state-overlay" data-testid="empty-state">
                <p>まだナレッジグラフがありません</p>
                <p>Nodeを追加してグラフを構築してください。</p>
                <div className="btn-row">
                  <button type="button" onClick={handleAddNode}>
                    Nodeを追加
                  </button>
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
        right={
          <Inspector
            mode={resolvedMode}
            selectedNode={selectedNode}
            selectedEdge={selectedEdge}
            nodes={nodes}
            edges={edges}
            onRefresh={() => loadGraph(searchQuery || undefined)}
            onClearSelection={handleClearSelection}
            onSelectNode={handleNodeSelect}
            onSelectEdge={handleEdgeSelect}
            onCancelCreate={() => setInspectorMode("empty")}
          />
        }
      />
      <StatusBar
        nodeCount={nodes.length}
        edgeCount={edges.length}
        selection={selectionLabel}
        zoom={zoom}
      />
    </>
  );
}
