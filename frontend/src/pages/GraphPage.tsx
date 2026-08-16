import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, Edge, Node, Relationship } from "../api/client";
import ContextMenu from "../components/ui/ContextMenu";
import GraphCanvas, { type GraphCanvasHandle } from "../features/graph/GraphCanvas";
import GraphControls from "../features/graph/GraphControls";
import RelationshipPickerDialog from "../features/graph/RelationshipPickerDialog";
import type { LayoutName } from "../features/graph/nodeStyles";
import { useGraphState } from "../features/graph/useGraphState";
import Inspector, { type InspectorMode } from "../features/inspector/Inspector";
import LeftNavigator from "../features/navigator/LeftNavigator";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";
import { useToast } from "../hooks/useToast";
import { useUndoRedo } from "../hooks/useUndoRedo";
import ThreeColumnLayout from "../layout/ThreeColumnLayout";
import StatusBar from "../layout/StatusBar";
import { validateEdge } from "../utils/graphValidation";
import { slugFromLabel, uniqueId } from "../utils/idSlug";

export default function GraphPage() {
  const [searchParams] = useSearchParams();
  const [allNodes, setAllNodes] = useState<Node[]>([]);
  const [allEdges, setAllEdges] = useState<Edge[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [pendingConnection, setPendingConnection] = useState<{
    sourceId: string;
    targetId: string;
  } | null>(null);
  const [connectError, setConnectError] = useState("");
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
  const { showToast } = useToast();
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
    void api.listRelationships().then(setRelationships).catch(() => setRelationships([]));
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
    (node: Node) => {
      setInspectorMode("node");
      setDrawerOpen(true);
      selectNode(node);
      canvasRef.current?.centerOnNode(node.id);
    },
    [selectNode],
  );

  const handleNodeExpand = useCallback(
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

  const handleAddNode = useCallback(() => {
    clearSelection();
    setInspectorMode("create-node");
    setDrawerOpen(true);
  }, [clearSelection]);

  const handleAddRelationship = useCallback(() => {
    setInspectorMode("create-edge");
    setDrawerOpen(true);
  }, []);

  const handleConnectRequest = useCallback((sourceId: string, targetId: string) => {
    setConnectError("");
    setPendingConnection({ sourceId, targetId });
  }, []);

  const handleConfirmConnection = useCallback(
    async (predicate: string) => {
      if (!pendingConnection) return;
      const { sourceId, targetId } = pendingConnection;
      const validation = validateEdge(
        { subject: sourceId, predicate, object: targetId },
        relationships,
        allNodes,
        { existingEdges: allEdges },
      );
      if (!validation.valid) {
        const msg = validation.formError ?? Object.values(validation.fieldErrors)[0] ?? "入力内容を確認してください";
        setConnectError(msg);
        showToast("error", msg);
        return;
      }

      try {
        const id = uniqueId(
          slugFromLabel(`${predicate}-${sourceId}-${targetId}`),
          new Set(allEdges.map((e) => e.id)),
        );
        const created = await api.createEdge({
          id,
          subject: sourceId,
          predicate,
          object: targetId,
          properties: {},
        });
        setPendingConnection(null);
        setConnectError("");
        showToast("success", "Relationshipを作成しました");
        await loadGraph(searchQuery || undefined);
        handleEdgeSelect(created);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Relationshipの作成に失敗しました";
        setConnectError(msg);
        showToast("error", msg);
      }
    },
    [
      pendingConnection,
      relationships,
      allNodes,
      allEdges,
      loadGraph,
      searchQuery,
      handleEdgeSelect,
      showToast,
    ],
  );

  const handleClearSelection = useCallback(() => {
    clearSelection();
    setInspectorMode("empty");
    setDrawerOpen(false);
  }, [clearSelection]);

  const handleDeleteSelected = useCallback(async () => {
    try {
      if (selectedNode) {
        push({ type: "node", action: "delete", before: selectedNode, after: null });
        await api.deleteNode(selectedNode.id);
        clearSelection();
        setInspectorMode("empty");
        setDrawerOpen(false);
        loadGraph(searchQuery || undefined);
      } else if (selectedEdge) {
        push({ type: "edge", action: "delete", before: selectedEdge, after: null });
        await api.deleteEdge(selectedEdge.id);
        clearSelection();
        setInspectorMode("empty");
        setDrawerOpen(false);
        loadGraph(searchQuery || undefined);
      }
    } catch {
      /* ignore */
    }
  }, [selectedNode, selectedEdge, push, clearSelection, loadGraph, searchQuery]);

  const handleContextMenu = useCallback(
    (x: number, y: number, target: "node" | "edge" | "canvas", id?: string) => {
      if (target === "node" && id) {
        const node = allNodes.find((n) => n.id === id);
        if (!node) return;
        setContextMenu({
          x,
          y,
          items: [
            { label: "Nodeを編集", action: () => handleNodeSelect(node) },
            {
              label: "関係を追加",
              action: () => {
                selectNode(node);
                setInspectorMode("create-edge");
                setDrawerOpen(true);
              },
            },
            { label: "周辺ノードを展開", action: () => void handleNodeExpand(node) },
            {
              label: "削除",
              action: () => {
                selectNode(node);
                void handleDeleteSelected();
              },
              danger: true,
            },
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
            {
              label: "削除",
              action: () => {
                selectEdge(edge);
                void handleDeleteSelected();
              },
              danger: true,
            },
          ],
        });
      } else if (target === "canvas") {
        setContextMenu({
          x,
          y,
          items: [{ label: "Nodeを追加", action: handleAddNode }],
        });
      }
    },
    [allNodes, allEdges, handleNodeSelect, handleNodeExpand, handleEdgeSelect, selectNode, selectEdge, handleAddNode, handleDeleteSelected],
  );

  const handleZoomChange = useCallback((z: number) => setZoom(z), [setZoom]);

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
              onConnectRequest={handleConnectRequest}
              selectedNodeId={selectedNode?.id ?? null}
              selectedEdgeId={selectedEdge?.id ?? null}
              onContextMenu={handleContextMenu}
              onZoomChange={handleZoomChange}
            />
            <p className="graph-hint">選択ノード右の●をドラッグして Relationship を作成できます</p>
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
      {pendingConnection && (
        <RelationshipPickerDialog
          open
          sourceNode={
            allNodes.find((n) => n.id === pendingConnection.sourceId) ?? {
              id: pendingConnection.sourceId,
              label: pendingConnection.sourceId,
              type: "",
              properties: {},
            }
          }
          targetNode={
            allNodes.find((n) => n.id === pendingConnection.targetId) ?? {
              id: pendingConnection.targetId,
              label: pendingConnection.targetId,
              type: "",
              properties: {},
            }
          }
          relationships={relationships}
          error={connectError}
          onConfirm={(predicate) => void handleConfirmConnection(predicate)}
          onCancel={() => {
            setPendingConnection(null);
            setConnectError("");
          }}
        />
      )}
    </>
  );
}
