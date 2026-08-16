import { useEffect, useImperativeHandle, useRef, forwardRef } from "react";
import cytoscape, { Core } from "cytoscape";
import type { Edge, Node } from "../../api/client";
import { graphSignature, syncGraphElements } from "./graphSync";
import {
  buildCytoscapeStyles,
  LAYOUT_OPTIONS,
  type LayoutName,
} from "./nodeStyles";

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
    selectedNodeId,
    selectedEdgeId,
  },
  ref,
) {
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

  nodesRef.current = nodes;
  edgesRef.current = edges;
  onNodeSelectRef.current = onNodeSelect;
  onEdgeSelectRef.current = onEdgeSelect;
  onNodeExpandRef.current = onNodeExpand;
  onBackgroundClickRef.current = onBackgroundClick;
  onContextMenuRef.current = onContextMenu;
  onZoomChangeRef.current = onZoomChange;

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

    return () => {
      cy.destroy();
      cyRef.current = null;
      layoutAppliedRef.current = false;
      signatureRef.current = "";
    };
  }, []);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const nextSignature = graphSignature(nodes, edges);
    if (nextSignature === signatureRef.current) return;

    const hadElements = signatureRef.current !== "";
    signatureRef.current = nextSignature;
    const changed = syncGraphElements(cy, nodes, edges);

    if (!layoutAppliedRef.current && nodes.length > 0) {
      cy.layout({ ...LAYOUT_OPTIONS[layout], animate: false }).run();
      layoutAppliedRef.current = true;
      prevLayoutRef.current = layout;
    } else if (changed && hadElements) {
      // Preserve positions; no re-layout on incremental updates
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

  return <div ref={containerRef} className="graph-canvas" data-testid="graph-canvas" />;
});

export default GraphCanvas;
