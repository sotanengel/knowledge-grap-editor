import type { Core } from "cytoscape";
import type { Edge, Node } from "../../api/client";
import { buildNodeLabel } from "./nodeStyles";

function getPrimaryAttr(node: Node): string | undefined {
  const props = node.properties;
  return props.email ?? props.name ?? props.description ?? undefined;
}

export function graphSignature(nodes: Node[], edges: Edge[]): string {
  const nodePart = nodes.map((n) => `${n.id}:${n.label}:${n.type}`).join("|");
  const edgePart = edges.map((e) => `${e.id}:${e.subject}:${e.predicate}:${e.object}`).join("|");
  return `${nodePart};;${edgePart}`;
}

export function syncGraphElements(cy: Core, nodes: Node[], edges: Edge[]): boolean {
  const nextNodeIds = new Set(nodes.map((n) => n.id));
  const nextEdgeIds = new Set(edges.map((e) => e.id));

  let changed = false;

  cy.nodes().forEach((ele) => {
    if (!nextNodeIds.has(ele.id())) {
      ele.remove();
      changed = true;
    }
  });

  cy.edges().forEach((ele) => {
    if (!nextEdgeIds.has(ele.id())) {
      ele.remove();
      changed = true;
    }
  });

  for (const n of nodes) {
    const existing = cy.getElementById(n.id);
    const displayLabel = buildNodeLabel(n.type, n.label, getPrimaryAttr(n));
    const data = { id: n.id, label: n.label, type: n.type, displayLabel };
    if (existing.empty()) {
      cy.add({ group: "nodes", data });
      changed = true;
    } else {
      existing.data(data);
    }
  }

  for (const e of edges) {
    const existing = cy.getElementById(e.id);
    const data = {
      id: e.id,
      source: e.subject,
      target: e.object,
      label: e.predicate,
    };
    if (existing.empty()) {
      cy.add({ group: "edges", data });
      changed = true;
    } else {
      existing.data(data);
    }
  }

  return changed;
}
