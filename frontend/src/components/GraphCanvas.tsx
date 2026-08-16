import { useEffect, useRef } from "react";
import cytoscape, { Core } from "cytoscape";
import type { Edge, Node } from "../api/client";

interface Props {
  nodes: Node[];
  edges: Edge[];
  onNodeSelect?: (node: Node) => void;
  onEdgeSelect?: (edge: Edge) => void;
}

export default function GraphCanvas({ nodes, edges, onNodeSelect, onEdgeSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (!cyRef.current) {
      cyRef.current = cytoscape({
        container: containerRef.current,
        style: [
          {
            selector: "node",
            style: {
              label: "data(label)",
              "background-color": "#3182ce",
              color: "#fff",
              "text-valign": "center",
              "text-halign": "center",
              "font-size": "10px",
              width: 60,
              height: 60,
            },
          },
          {
            selector: "node[type]",
            style: {
              "border-width": 2,
              "border-color": "#2c5282",
            },
          },
          {
            selector: "edge",
            style: {
              label: "data(label)",
              width: 2,
              "line-color": "#718096",
              "target-arrow-color": "#718096",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              "font-size": "9px",
            },
          },
          {
            selector: ":selected",
            style: {
              "background-color": "#e53e3e",
              "line-color": "#e53e3e",
              "target-arrow-color": "#e53e3e",
            },
          },
        ],
        layout: { name: "cose", animate: false },
      });
      cyRef.current.on("tap", "node", (evt) => {
        const id = evt.target.id();
        const node = nodes.find((n) => n.id === id);
        if (node && onNodeSelect) onNodeSelect(node);
      });
      cyRef.current.on("tap", "edge", (evt) => {
        const id = evt.target.id();
        const edge = edges.find((e) => e.id === id);
        if (edge && onEdgeSelect) onEdgeSelect(edge);
      });
    }

    const cy = cyRef.current;
    cy.elements().remove();
    cy.add(
      nodes.map((n) => ({
        group: "nodes" as const,
        data: { id: n.id, label: n.label, type: n.type },
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
    cy.layout({ name: "cose", animate: true }).run();
  }, [nodes, edges, onNodeSelect, onEdgeSelect]);

  return <div ref={containerRef} className="graph-canvas" data-testid="graph-canvas" />;
}
