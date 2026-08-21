/** Cytoscape styling. Derived triples are dashed and pale; violations get a red rim. */
import type { StylesheetStyle } from 'cytoscape';

export const GRAPH_STYLE: StylesheetStyle[] = [
  {
    selector: 'node',
    style: {
      'background-color': '#e2e8f0',
      'border-width': 1,
      'border-color': '#94a3b8',
      label: 'data(label)',
      color: '#0f172a',
      'font-size': 12,
      'text-valign': 'center',
      'text-halign': 'center',
      'text-wrap': 'ellipsis',
      'text-max-width': '120px',
      shape: 'round-rectangle',
      width: 'label',
      height: 28,
      padding: '10px',
    },
  },
  {
    selector: 'node:selected',
    style: { 'border-width': 3, 'border-color': '#2563eb', 'background-color': '#dbeafe' },
  },
  {
    selector: 'node.violated',
    style: { 'border-width': 3, 'border-color': '#dc2626', 'background-color': '#fee2e2' },
  },
  {
    selector: 'node.focus',
    style: { 'border-width': 3, 'border-color': '#f59e0b' },
  },
  {
    selector: 'edge',
    style: {
      width: 1.5,
      'line-color': '#94a3b8',
      'target-arrow-color': '#94a3b8',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      label: 'data(label)',
      'font-size': 10,
      color: '#475569',
      'text-background-color': '#ffffff',
      'text-background-opacity': 0.85,
      'text-background-padding': '2px',
    },
  },
  {
    // Inference output: visibly not something you typed, and not editable.
    selector: 'edge.inferred',
    style: {
      'line-style': 'dashed',
      'line-color': '#cbd5e1',
      'target-arrow-color': '#cbd5e1',
      color: '#94a3b8',
      opacity: 0.85,
    },
  },
  {
    selector: 'edge:selected',
    style: { 'line-color': '#2563eb', 'target-arrow-color': '#2563eb', width: 2.5 },
  },
  {
    selector: '.eh-handle',
    style: {
      'background-color': '#2563eb',
      width: 10,
      height: 10,
      shape: 'ellipse',
      'overlay-opacity': 0,
      'border-width': 8,
      'border-opacity': 0,
    },
  },
  {
    selector: '.eh-ghost-edge, .eh-preview',
    style: { 'line-color': '#2563eb', 'target-arrow-color': '#2563eb' },
  },
  { selector: '.eh-ghost-edge.eh-preview-active', style: { opacity: 0 } },
];

/** Room left around the graph when it is fitted to the viewport. */
export const FIT_PADDING = 48;

export const LAYOUT = {
  name: 'fcose',
  animate: false,
  // Without randomising, every node starts at the same point and fcose has
  // nothing to push apart, which collapses the graph into one corner.
  randomize: true,
  nodeRepulsion: 12000,
  idealEdgeLength: 160,
  nodeSeparation: 120,
  fit: true,
  padding: FIT_PADDING,
} as const;
