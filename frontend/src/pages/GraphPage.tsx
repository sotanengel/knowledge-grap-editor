import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, Edge, Node } from "../api/client";
import ContextMenu from "../components/ui/ContextMenu";
import GraphCanvas, { type GraphCanvasHandle } from "../features/graph/GraphCanvas";
import GraphControls from "../features/graph/GraphControls";
import type { LayoutName } from "../features/graph/nodeStyles";
import { useGraphState } from "../features/graph/useGraphState";
import Inspector, { type InspectorMode } from "../features/inspector/Inspector";
import LeftNavigator from "../features/navigator/LeftNavigator";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";
import { useUndoRedo } from "../hooks/useUndoRedo";
import ThreeColumnLayout from "../layout/ThreeColumnLayout";
import StatusBar from "../layout/StatusBar";

export default function GraphPage() {
  const [searchParams] = useSearchParams();
  const [allNodes, setAllNodes] = useState<Node[]>([]);
  const [allEdges, setAllEdges] = useState<Edge[]>([]);
  const [searchQuery, setSearchQuery] = useState(searchParams.get("q") || "");
  const [searchResults, setSearchResults] = useState<Node[]>([]);
  const [depth, setDepth] = useState(1);
  const [status, setStatus] = useState("");
  const [inspectorMode, setInspectorMode] = useState<InspectorMode>("empty");
  const [layout, setLayout] = useState<LayoutName>("force");
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedClasses, setSelectedClasses] = useState<Set<string>>(new Set());
  const [selectedRelationships, setSelectedRelationships] = useState<Set<string>>(new Set());
  const [displaySettings, setDisplaySettings] = useState({
    showNodeType: true,
    showRelationship: true,
    showLabel: true,
    showDescription: false,
  });
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    items: Array<{ label: string; action: () => void; danger?: boolean }>;
  } | null>(null);
  const canvasRef = useRef<GraphCanvasHandle>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const { push } = useUndoRedo();
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
        setAllNodes(result.nodes);
        setAllEdges(result.edges);
      } else {
        const [n, e] = await Promise.all([api.listNodes(), api.listEdges()]);
        setAllNodes(n);
        setAllEdges(e);
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

  const nodes = useMemo(() => {
    if (selectedClasses.size === 0) return allNodes;
    return allNodes.filter((n) => selectedClasses.has(n.type));
  }, [allNodes, selectedClasses]);

  const edges = useMemo(() => {
    let filtered = allEdges;
    if (selectedRelationships.size > 0) {
      filtered = filtered.filter((e) => selectedRelationships.has(e.predicate));
    }
    if (selectedClasses.size > 0) {
      const nodeIds = new Set(nodes.map((n) => n.id));
      filtered = filtered.filter((e) => nodeIds.has(e.subject) && nodeIds.has(e.object));
    }
    return filtered;
  }, [allEdges, nodes, selectedClasses, selectedRelationships]);

  const classList = useMemo(() => [...new Set(allNodes.map((n) => n.type))].sort(), [allNodes]);
  const relList = useMemo(
    () => [...new Set(allEdges.map((e) => e.predicate))].sort(),
    [allEdges],
  );

  const handleSearch = useCallback(async (q: string) => {
    try {
      const result = await api.searchGraph(q);
      setSearchResults(result.nodes);
    } catch {
      setSearchResults([]);
    }
  }, []);

  const handleNodeSelect = useCallback(
    async (node: Node) => {
      setInspectorMode("node");
      setDrawerOpen(true);
      selectNode(node);
      canvasRef.current?.centerOnNode(node.id);
      try {
        const neighbors = await api.getNeighbors(node.id, depth);
        setAllNodes(neighbors.nodes);
        setAllEdges(neighbors.edges);
      } catch {
        /* keep */
      }
    },
    [depth, selectNode],
  );

  const handleEdgeSelect = useCallback(
    (edge: Edge) => {
      setInspectorMode("edge");
      setDrawerOpen(true);
      selectEdge(edge);
    },
    [selectEdge],
  );

  const handleNodeExpand = useCallback(
    async (node: Node) => {
      await handleNodeSelect(node);
    },
    [handleNodeSelect],
  );

  const handleAddNode = () => {
    clearSelection();
    setInspectorMode("create-node");
    setDrawerOpen(true);
  };

  const handleAddRelationship = () => {
    setInspectorMode("create-edge");
    setDrawerOpen(true);
  };

  const handleClearSelection = () => {
    clearSelection();
    setInspectorMode("empty");
    setDrawerOpen(false);
  };

  const handleDeleteSelected = async () => {
    try {
      if (selectedNode) {
        push({ type: "node", action: "delete", before: selectedNode, after: null });
        await api.deleteNode(selectedNode.id);
        handleClearSelection();
        loadGraph(searchQuery || undefined);
      } else if (selectedEdge) {
        push({ type: "edge", action: "delete", before: selectedEdge, after: null });
        await api.deleteEdge(selectedEdge.id);
        handleClearSelection();
        loadGraph(searchQuery || undefined);
      }
    } catch {
      /* ignore */
    }
  };

  useKeyboardShortcuts({
    onAddNode: handleAddNode,
    onAddEdge: handleAddRelationship,
    onDelete: handleDeleteSelected,
    onEscape: () => {
      setContextMenu(null);
      handleClearSelection();
    },
    onSearch: () => searchInputRef.current?.focus(),
  });

  useEffect(() => {
    const timer = setInterval(() => {
      if (canvasRef.current) setZoom(canvasRef.current.getZoom());
    }, 500);
    return () => clearInterval(timer);
  }, [setZoom]);

  useEffect(() => {
    canvasRef.current?.setLayout(layout);
  }, [layout, nodes, edges]);

  const isEmpty = allNodes.length === 0 && allEdges.length === 0 && !status;

  const resolvedMode: InspectorMode =
    inspectorMode === "create-node" || inspectorMode === "create-edge"
      ? inspectorMode
      : selectedNode
        ? "node"
        : selectedEdge
          ? "edge"
          : "empty";

  const toggleClass = (id: string) => {
    setSelectedClasses((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleRelationship = (id: string) => {
    setSelectedRelationships((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <>
      <ThreeColumnLayout
        leftCollapsed={leftCollapsed}
        rightDrawerOpen={drawerOpen}
        left={
          <LeftNavigator
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onSearch={handleSearch}
            searchResults={searchResults}
            onSelectResult={handleNodeSelect}
            depth={depth}
            onDepthChange={setDepth}
            classes={classList}
            relationships={relList}
            selectedClasses={selectedClasses}
            selectedRelationships={selectedRelationships}
            onToggleClass={toggleClass}
            onToggleRelationship={toggleRelationship}
            displaySettings={displaySettings}
            onDisplayChange={(key, value) => {
              const map: Record<string, keyof typeof displaySettings> = {
                nodeType: "showNodeType",
                relationship: "showRelationship",
                label: "showLabel",
                description: "showDescription",
              };
              const field = map[key];
              if (field) setDisplaySettings((s) => ({ ...s, [field]: value }));
            }}
            onAddNode={handleAddNode}
            onAddRelationship={handleAddRelationship}
            leftCollapsed={leftCollapsed}
            onToggleCollapse={() => setLeftCollapsed((c) => !c)}
          />
        }
        center={
          <div className="graph-area">
            <GraphCanvas
              ref={canvasRef}
              nodes={nodes}
              edges={edges}
              layout={layout}
              onNodeSelect={handleNodeSelect}
              onEdgeSelect={handleEdgeSelect}
              onNodeExpand={handleNodeExpand}
              onBackgroundClick={handleClearSelection}
              selectedNodeId={selectedNode?.id ?? null}
              selectedEdgeId={selectedEdge?.id ?? null}
              onContextMenu={(x, y, target, id) => {
                if (target === "node" && id) {
                  const node = allNodes.find((n) => n.id === id);
                  if (!node) return;
                  setContextMenu({
                    x,
                    y,
                    items: [
                      { label: "Nodeを編集", action: () => handleNodeSelect(node) },
                      { label: "関係を追加", action: () => {
                        selectNode(node);
                        handleAddRelationship();
                      }},
                      { label: "周辺ノードを展開", action: () => handleNodeExpand(node) },
                      { label: "削除", action: () => {
                        selectNode(node);
                        void handleDeleteSelected();
                      }, danger: true },
                    ],
                  });
                } else if (target === "edge" && id) {
                  const edge = allEdges.find((e) => e.id === id);
                  if (!edge) return;
                  setContextMenu({
                    x,
                    y,
                    items: [
                      { label: "Relationshipを編集", action: () => handleEdgeSelect(edge) },
                      { label: "削除", action: () => {
                        selectEdge(edge);
                        void handleDeleteSelected();
                      }, danger: true },
                    ],
                  });
                } else if (target === "canvas") {
                  setContextMenu({
                    x,
                    y,
                    items: [{ label: "Nodeを追加", action: handleAddNode }],
                  });
                }
              }}
            />
            <GraphControls
              layout={layout}
              onLayoutChange={setLayout}
              onZoomIn={() => canvasRef.current?.zoomIn()}
              onZoomOut={() => canvasRef.current?.zoomOut()}
              onFit={() => canvasRef.current?.fit()}
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
            nodes={allNodes}
            edges={allEdges}
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
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={contextMenu.items}
          onClose={() => setContextMenu(null)}
        />
      )}
    </>
  );
}
