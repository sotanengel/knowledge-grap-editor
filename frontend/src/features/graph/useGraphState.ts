import { useCallback, useState } from "react";
import type { Edge, Node } from "../../api/client";

export function useGraphState() {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<Edge | null>(null);
  const [zoom, setZoom] = useState(1);

  const selectNode = useCallback((node: Node | null) => {
    setSelectedNode(node);
    setSelectedEdge(null);
  }, []);

  const selectEdge = useCallback((edge: Edge | null) => {
    setSelectedEdge(edge);
    setSelectedNode(null);
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
  }, []);

  const selectionLabel = selectedNode
    ? `Selected: ${selectedNode.label}`
    : selectedEdge
      ? `Selected: ${selectedEdge.predicate}`
      : "";

  return {
    selectedNode,
    selectedEdge,
    selectNode,
    selectEdge,
    clearSelection,
    zoom,
    setZoom,
    selectionLabel,
  };
}
