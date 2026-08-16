import { useCallback, useEffect, useImperativeHandle, useRef, useState, forwardRef } from "react";
import cytoscape, { Core, NodeSingular } from "cytoscape";
import edgehandles from "cytoscape-edgehandles";
import type { Edge, Node } from "../../api/client";
import { graphSignature, syncGraphElements } from "./graphSync";
import {
  buildCytoscapeStyles,
  LAYOUT_OPTIONS,
  type LayoutName,
} from "./nodeStyles";

cytoscape.use(edgehandles);

interface EdgeHandlesInstance {
  enable: () => void;
  disable: () => void;
  destroy: () => void;
  start: (node: NodeSingular) => void;
  stop: () => void;
}

export interface GraphCanvasHandle {
  fit: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
  setLayout: (layout: LayoutName) => void;
  centerOnNode: (nodeId: string) => void;
  getZoom: () => number;
}

interface Props {
  nodes: Node[];
  edges: Edge[];
  layout?: LayoutName;
  onNodeSelect?: (node: Node) => void;
  onEdgeSelect?: (edge: Edge) => void;
  onNodeExpand?: (node: Node) => void;
  onBackgroundClick?: () => void;
  onContextMenu?: (x: number, y: number, target: "node" | "edge" | "canvas", id?: string) => void;
  onZoomChange?: (zoom: number) => void;
  onConnectRequest?: (sourceId: string, targetId: string) => void;
  connectMode?: boolean;
  selectedNodeId?: string | null;
  selectedEdgeId?: string | null;
}

const GraphCanvas = forwardRef<GraphCanvasHandle, Props>(function GraphCanvas(
  {
    nodes,
    edges,
    layout = "force",
    onNodeSelect,
    onEdgeSelect,
    onNodeExpand,
    onBackgroundClick,
    onContextMenu,
    onZoomChange,
    onConnectRequest,
    connectMode = true,
    selectedNodeId,
    selectedEdgeId,
  },
  ref,
) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);
  const signatureRef = useRef("");
  const layoutAppliedRef = useRef(false);
  const prevLayoutRef = useRef<LayoutName | null>(null);
  const onNodeSelectRef = useRef(onNodeSelect);
  const onEdgeSelectRef = useRef(onEdgeSelect);
  const onNodeExpandRef = useRef(onNodeExpand);
  const onBackgroundClickRef = useRef(onBackgroundClick);
  const onContextMenuRef = useRef(onContextMenu);
  const onZoomChangeRef = useRef(onZoomChange);
  const onConnectRequestRef = useRef(onConnectRequest);
  const connectModeRef = useRef(connectMode);
  const edgeHandlesRef = useRef<EdgeHandlesInstance | null>(null);
  const connectingRef = useRef(false);
  const [handlePos, setHandlePos] = useState<{ x: number; y: number } | null>(null);

  nodesRef.current = nodes;
  edgesRef.current = edges;
  onNodeSelectRef.current = onNodeSelect;
  onEdgeSelectRef.current = onEdgeSelect;
  onNodeExpandRef.current = onNodeExpand;
  onBackgroundClickRef.current = onBackgroundClick;
  onContextMenuRef.current = onContextMenu;
  onZoomChangeRef.current = onZoomChange;
  onConnectRequestRef.current = onConnectRequest;
  connectModeRef.current = connectMode;

  const updateHandlePosition = useCallback(() => {
    const cy = cyRef.current;
    if (!cy || !selectedNodeId || !connectModeRef.current) {
      setHandlePos(null);
      return;
    }
    const ele = cy.getElementById(selectedNodeId);
    if (ele.empty()) {
      setHandlePos(null);
      return;
    }
    const rp = ele.renderedPosition();
    const w = ele.renderedOuterWidth();
    setHandlePos({ x: rp.x + w / 2 + 8, y: rp.y });
  }, [selectedNodeId]);

  useImperativeHandle(ref, () => ({
    fit: () => cyRef.current?.fit(undefined, 40),
    zoomIn: () => cyRef.current?.zoom(cyRef.current.zoom() * 1.2),
    zoomOut: () => cyRef.current?.zoom(cyRef.current.zoom() / 1.2),
    setLayout: (name: LayoutName) => {
      cyRef.current?.layout({ ...LAYOUT_OPTIONS[name], animate: true }).run();
    },
    centerOnNode: (nodeId: string) => {
      const cy = cyRef.current;
      if (!cy) return;
      const ele = cy.getElementById(nodeId);
      if (ele.nonempty()) {
        cy.animate({ center: { eles: ele }, duration: 200 });
      }
    },
    getZoom: () => cyRef.current?.zoom() ?? 1,
  }));

  useEffect(() => {
    if (!containerRef.current || cyRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      style: buildCytoscapeStyles(),
      wheelSensitivity: 0.3,
      boxSelectionEnabled: true,
    });
    cyRef.current = cy;

    cy.on("tap", "node", (evt) => {
      const id = evt.target.id();
      const node = nodesRef.current.find((n) => n.id === id);
      if (node) onNodeSelectRef.current?.(node);
    });

    cy.on("tap", "edge", (evt) => {
      const id = evt.target.id();
      const edge = edgesRef.current.find((e) => e.id === id);
      if (edge) onEdgeSelectRef.current?.(edge);
    });

    cy.on("dbltap", "node", (evt) => {
      const id = evt.target.id();
      const node = nodesRef.current.find((n) => n.id === id);
      if (node) onNodeExpandRef.current?.(node);
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) onBackgroundClickRef.current?.();
    });

    cy.on("cxttap", "node", (evt) => {
      evt.preventDefault();
      const pos = evt.originalEvent as MouseEvent;
      onContextMenuRef.current?.(pos.clientX, pos.clientY, "node", evt.target.id());
    });

    cy.on("cxttap", "edge", (evt) => {
      evt.preventDefault();
      const pos = evt.originalEvent as MouseEvent;
      onContextMenuRef.current?.(pos.clientX, pos.clientY, "edge", evt.target.id());
    });

    cy.on("cxttap", (evt) => {
      if (evt.target === cy) {
        const pos = evt.originalEvent as MouseEvent;
        onContextMenuRef.current?.(pos.clientX, pos.clientY, "canvas");
      }
    });

    cy.on("zoom", () => {
      onZoomChangeRef.current?.(cy.zoom());
    });

    cy.on("ehcomplete", (_evt, sourceNode, targetNode, addedEdge) => {
      addedEdge.remove();
      if (!connectModeRef.current) return;
      const sourceId = sourceNode.id();
      const targetId = targetNode.id();
      if (sourceId === targetId) return;
      onConnectRequestRef.current?.(sourceId, targetId);
    });

    const eh = cy.edgehandles({
      snap: true,
      snapThreshold: 40,
      canConnect: (sourceNode, targetNode) => !sourceNode.same(targetNode),
    }) as EdgeHandlesInstance;
    edgeHandlesRef.current = eh;
    if (connectMode) eh.enable();

    return () => {
      edgeHandlesRef.current?.destroy();
      edgeHandlesRef.current = null;
      cy.destroy();
      cyRef.current = null;
      layoutAppliedRef.current = false;
      signatureRef.current = "";
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional single init
  }, []);

  useEffect(() => {
    const eh = edgeHandlesRef.current;
    if (!eh) return;
    if (connectMode) eh.enable();
    else eh.disable();
  }, [connectMode]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const nextSignature = graphSignature(nodes, edges);
    if (nextSignature === signatureRef.current) return;

    const hadElements = signatureRef.current !== "";
    signatureRef.current = nextSignature;
    syncGraphElements(cy, nodes, edges);

    if (!layoutAppliedRef.current && nodes.length > 0) {
      cy.layout({ ...LAYOUT_OPTIONS[layout], animate: false }).run();
      layoutAppliedRef.current = true;
      prevLayoutRef.current = layout;
    } else if (hadElements) {
      // Preserve positions on incremental updates
    }
  }, [nodes, edges, layout]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !layoutAppliedRef.current) return;
    if (prevLayoutRef.current === layout) return;
    prevLayoutRef.current = layout;
    cy.layout({ ...LAYOUT_OPTIONS[layout], animate: true }).run();
  }, [layout]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.nodes().removeClass("edge-endpoint");
    cy.$(":selected").unselect();

    if (selectedNodeId) {
      const ele = cy.getElementById(selectedNodeId);
      if (ele.nonempty()) ele.select();
    } else if (selectedEdgeId) {
      const edge = edgesRef.current.find((e) => e.id === selectedEdgeId);
      cy.getElementById(selectedEdgeId).select();
      if (edge) {
        cy.getElementById(edge.subject).addClass("edge-endpoint");
        cy.getElementById(edge.object).addClass("edge-endpoint");
      }
    }
  }, [selectedNodeId, selectedEdgeId]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    updateHandlePosition();
    cy.on("pan zoom resize render", updateHandlePosition);
    return () => {
      if (typeof cy.off === "function") {
        cy.off("pan zoom resize render", updateHandlePosition);
      }
    };
  }, [updateHandlePosition, nodes, edges, layout]);

  const handleConnectMouseDown = (event: React.MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    const cy = cyRef.current;
    const eh = edgeHandlesRef.current;
    if (!cy || !eh || !selectedNodeId || !connectMode) return;

    const node = cy.getElementById(selectedNodeId);
    if (node.empty()) return;

    connectingRef.current = true;
    eh.start(node);

    const onMouseUp = () => {
      window.removeEventListener("mouseup", onMouseUp);
      if (connectingRef.current) {
        eh.stop();
        connectingRef.current = false;
      }
    };
    window.addEventListener("mouseup", onMouseUp);
  };

  return (
    <div ref={wrapperRef} className="graph-canvas-wrapper">
      <div ref={containerRef} className="graph-canvas" data-testid="graph-canvas" />
      {connectMode && handlePos && selectedNodeId && (
        <button
          type="button"
          className="connect-handle"
          aria-label="Relationshipを作成"
          style={{ left: handlePos.x, top: handlePos.y }}
          onMouseDown={handleConnectMouseDown}
        />
      )}
    </div>
  );
});

export default GraphCanvas;
