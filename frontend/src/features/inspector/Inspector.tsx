import type { Edge, Node } from "../../api/client";
import EdgeInspector from "./EdgeInspector";
import EmptyInspector from "./EmptyInspector";
import NodeInspector from "./NodeInspector";

interface Props {
  selectedNode?: Node | null;
  selectedEdge?: Edge | null;
  nodes?: Node[];
  edges?: Edge[];
  onRefresh?: () => void;
  onClearSelection?: () => void;
  onSelectNode?: (node: Node) => void;
  onSelectEdge?: (edge: Edge) => void;
}

export default function Inspector({
  selectedNode,
  selectedEdge,
  nodes = [],
  edges = [],
  onRefresh,
  onClearSelection,
  onSelectNode,
  onSelectEdge,
}: Props) {
  return (
    <div className="inspector-panel" data-testid="inspector">
      {selectedNode ? (
        <NodeInspector
          key={selectedNode.id}
          node={selectedNode}
          nodes={nodes}
          edges={edges}
          onSave={() => onRefresh?.()}
          onDelete={() => {
            onClearSelection?.();
            onRefresh?.();
          }}
          onSelectEdge={onSelectEdge}
        />
      ) : selectedEdge ? (
        <EdgeInspector
          key={selectedEdge.id}
          edge={selectedEdge}
          nodes={nodes}
          onSave={() => onRefresh?.()}
          onDelete={() => {
            onClearSelection?.();
            onRefresh?.();
          }}
          onSelectNode={onSelectNode}
        />
      ) : (
        <EmptyInspector />
      )}
    </div>
  );
}
