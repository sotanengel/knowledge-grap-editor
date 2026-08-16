import { useEffect, useImperativeHandle, useRef, forwardRef } from "react";
import cytoscape, { Core } from "cytoscape";
import type { Edge, Node } from "../../api/client";
import {
  buildCytoscapeStyles,
  buildNodeLabel,
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
  selectedNodeId?: string | null;
  selectedEdgeId?: string | null;
}

function getPrimaryAttr(node: Node): string | undefined {
  const props = node.properties;
  return props.email ?? props.name ?? props.description ?? undefined;
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
    selectedNodeId,
    selectedEdgeId,
  },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);
  nodesRef.current = nodes;
  edgesRef.current = edges;

  useImperativeHandle(ref, () => ({
    fit: () => cyRef.current?.fit(undefined, 40),
    zoomIn: () => cyRef.current?.zoom(cyRef.current.zoom() * 1.2),
    zoomOut: () => cyRef.current?.zoom(cyRef.current.zoom() / 1.2),
    setLayout: (name: LayoutName) => {
      cyRef.current?.layout(LAYOUT_OPTIONS[name]).run();
    },
    centerOnNode: (nodeId: string) => {
      const cy = cyRef.current;
      if (!cy) return;
      const ele = cy.getElementById(nodeId);
      if (ele.nonempty()) {
        cy.center(ele);
        ele.select();
      }
    },
    getZoom: () => cyRef.current?.zoom() ?? 1,
  }));

  useEffect(() => {
    if (!containerRef.current) return;
    if (!cyRef.current) {
      cyRef.current = cytoscape({
        container: containerRef.current,
        style: buildCytoscapeStyles(),
        wheelSensitivity: 0.3,
        boxSelectionEnabled: true,
      });

      cyRef.current.on("tap", "node", (evt) => {
        const id = evt.target.id();
        const node = nodesRef.current.find((n) => n.id === id);
        if (node && onNodeSelect) onNodeSelect(node);
      });

      cyRef.current.on("tap", "edge", (evt) => {
        const id = evt.target.id();
        const edge = edgesRef.current.find((e) => e.id === id);
        if (edge && onEdgeSelect) onEdgeSelect(edge);
      });

      cyRef.current.on("dbltap", "node", (evt) => {
        const id = evt.target.id();
        const node = nodesRef.current.find((n) => n.id === id);
        if (node && onNodeExpand) onNodeExpand(node);
      });

      cyRef.current.on("tap", (evt) => {
        if (evt.target === cyRef.current) {
          onBackgroundClick?.();
        }
      });

      cyRef.current.on("cxttap", "node", (evt) => {
        evt.preventDefault();
        const pos = evt.originalEvent as MouseEvent;
        onContextMenu?.(pos.clientX, pos.clientY, "node", evt.target.id());
      });

      cyRef.current.on("cxttap", "edge", (evt) => {
        evt.preventDefault();
        const pos = evt.originalEvent as MouseEvent;
        onContextMenu?.(pos.clientX, pos.clientY, "edge", evt.target.id());
      });

      cyRef.current.on("cxttap", (evt) => {
        if (evt.target === cyRef.current) {
          const pos = evt.originalEvent as MouseEvent;
          onContextMenu?.(pos.clientX, pos.clientY, "canvas");
        }
      });
    }

    const cy = cyRef.current;
    cy.elements().remove();
    cy.add(
      nodes.map((n) => ({
        group: "nodes" as const,
        data: {
          id: n.id,
          label: n.label,
          type: n.type,
          displayLabel: buildNodeLabel(n.type, n.label, getPrimaryAttr(n)),
        },
      })),
    );
    cy.add(
      edges.map((e) => ({
        group: "edges" as const,
        data: {
          id: e.id,
          source: e.subject,
          target: e.object,
          label: e.predicate,
        },
      })),
    );
    cy.layout(LAYOUT_OPTIONS[layout]).run();
  }, [nodes, edges, layout, onNodeSelect, onEdgeSelect, onNodeExpand, onBackgroundClick, onContextMenu]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().removeClass("edge-endpoint");
    cy.$(":selected").unselect();
    if (selectedNodeId) {
      cy.getElementById(selectedNodeId).select();
    } else if (selectedEdgeId) {
      const edge = edges.find((e) => e.id === selectedEdgeId);
      cy.getElementById(selectedEdgeId).select();
      if (edge) {
        cy.getElementById(edge.subject).addClass("edge-endpoint");
        cy.getElementById(edge.object).addClass("edge-endpoint");
      }
    }
  }, [selectedNodeId, selectedEdgeId, edges]);

  return <div ref={containerRef} className="graph-canvas" data-testid="graph-canvas" />;
});

export default GraphCanvas;
