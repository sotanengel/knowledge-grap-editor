import type { Edge, Node } from "../../api/client";
import EdgeCreateForm from "./EdgeCreateForm";
import EdgeInspector from "./EdgeInspector";
import EmptyInspector from "./EmptyInspector";
import NodeCreateForm from "./NodeCreateForm";
import NodeInspector from "./NodeInspector";

export type InspectorMode = "empty" | "node" | "edge" | "create-node" | "create-edge";

interface Props {
  mode?: InspectorMode;
  selectedNode?: Node | null;
  selectedEdge?: Edge | null;
  nodes?: Node[];
  edges?: Edge[];
  onRefresh?: () => void;
  onClearSelection?: () => void;
  onSelectNode?: (node: Node) => void;
  onSelectEdge?: (edge: Edge) => void;
  onCancelCreate?: () => void;
}

export default function Inspector({
  mode = "empty",
  selectedNode,
  selectedEdge,
  nodes = [],
  edges = [],
  onRefresh,
  onClearSelection,
  onSelectNode,
  onSelectEdge,
  onCancelCreate,
}: Props) {
  return (
    <div className="inspector-panel" data-testid="inspector">
      {mode === "create-node" ? (
        <NodeCreateForm
          onCreated={() => {
            onCancelCreate?.();
            onRefresh?.();
          }}
          onCancel={() => onCancelCreate?.()}
        />
      ) : mode === "create-edge" ? (
        <EdgeCreateForm
          nodes={nodes}
          defaultSubject={selectedNode?.id}
          onCreated={() => {
            onCancelCreate?.();
            onRefresh?.();
          }}
          onCancel={() => onCancelCreate?.()}
        />
      ) : selectedNode ? (
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
