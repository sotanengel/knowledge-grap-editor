/**
 * Turning API documents into Cytoscape elements.
 *
 * Kept as a pure function so the mapping can be tested without a canvas: the
 * component around it only has to wire events.
 */
import type { EntityDocument } from '../api/types';
import { partition, labelOf, typesOf } from './entity';
import { localName, shortIri } from './iri';

export interface NodeData {
  id: string;
  label: string;
  types: string[];
  typeLabel: string;
  inferred: boolean;
  violated: boolean;
}

export interface EdgeData {
  id: string;
  source: string;
  target: string;
  predicate: string;
  label: string;
  inferred: boolean;
}

export interface CyElement {
  group: 'nodes' | 'edges';
  data: NodeData | EdgeData;
  position?: { x: number; y: number };
  classes?: string;
}

export interface BuildOptions {
  /** IRIs the reasoner produced; drawn dashed and not editable (§10.1). */
  inferredEdges?: Set<string>;
  /** Nodes SHACL flagged; drawn with a red border (§10.2). */
  violated?: Set<string>;
  /** Saved coordinates from the layout graph, so the canvas does not jump. */
  positions?: Record<string, { x: number; y: number }>;
  /** Labels for referenced nodes that are not themselves in the document set. */
  labels?: Record<string, string>;
}

export function edgeId(source: string, predicate: string, target: string): string {
  return `${source}|${predicate}|${target}`;
}

/** Build the element list for a set of entity documents. */
export function buildElements(
  documents: EntityDocument[],
  options: BuildOptions = {},
): CyElement[] {
  const inferred = options.inferredEdges ?? new Set<string>();
  const violated = options.violated ?? new Set<string>();
  const labels: Record<string, string> = { ...options.labels };

  for (const document of documents) {
    const label = labelOf(document);
    if (label) labels[document['@id']] = label;
  }

  const nodes = new Map<string, CyElement>();
  // Keyed by id: the same relation can be reached twice (a document listed
  // twice, or both ends loaded), and Cytoscape rejects a duplicate id.
  const edges = new Map<string, CyElement>();

  const ensureNode = (iri: string, document?: EntityDocument): void => {
    if (nodes.has(iri)) return;
    const types = document ? typesOf(document) : [];
    nodes.set(iri, {
      group: 'nodes',
      data: {
        id: iri,
        label: labels[iri] ?? localName(iri),
        types,
        typeLabel: types.map(shortIri).join(', '),
        inferred: false,
        violated: violated.has(iri),
      },
      ...(options.positions?.[iri] ? { position: options.positions[iri] } : {}),
      classes: violated.has(iri) ? 'violated' : undefined,
    });
  };

  for (const document of documents) {
    ensureNode(document['@id'], document);
  }

  for (const document of documents) {
    for (const relation of partition(document).relations) {
      if (relation.targetLabel) labels[relation.target] = relation.targetLabel;
      ensureNode(relation.target);
      const id = edgeId(document['@id'], relation.predicate, relation.target);
      const derived = inferred.has(id);
      edges.set(id, {
        group: 'edges',
        data: {
          id,
          source: document['@id'],
          target: relation.target,
          predicate: relation.predicate,
          label: localName(relation.predicate),
          inferred: derived,
        },
        classes: derived ? 'inferred' : undefined,
      });
    }
  }

  // Labels discovered while walking relations may name a node created earlier.
  for (const element of nodes.values()) {
    const data = element.data as NodeData;
    const label = labels[data.id];
    if (label) data.label = label;
  }

  return [...nodes.values(), ...edges.values()];
}

/**
 * Above this many nodes the canvas stops drawing everything at once and shows a
 * neighbourhood instead (§7.3-4).
 */
export const NEIGHBOURHOOD_THRESHOLD = 500;

export function needsNeighbourhoodMode(nodeCount: number, threshold = NEIGHBOURHOOD_THRESHOLD) {
  return nodeCount > threshold;
}
