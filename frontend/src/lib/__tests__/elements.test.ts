import { describe, expect, it } from 'vitest';

import type { EntityDocument } from '../../api/types';
import {
  NEIGHBOURHOOD_THRESHOLD,
  buildElements,
  edgeId,
  needsNeighbourhoodMode,
  type EdgeData,
  type NodeData,
} from '../elements';
import { RDFS_LABEL } from '../iri';

const WORKS_FOR = 'https://example.org/kg/ont#worksFor';
const ALICE = 'https://example.org/kg/id/alice';
const ACME = 'https://example.org/kg/id/acme';

const documents: EntityDocument[] = [
  {
    '@id': ALICE,
    '@type': ['https://example.org/kg/ont#Person'],
    [RDFS_LABEL]: [{ '@value': '田中太郎', '@language': 'ja' }],
    [WORKS_FOR]: [{ '@id': ACME }],
  },
  {
    '@id': ACME,
    [RDFS_LABEL]: [{ '@value': '株式会社アクメ', '@language': 'ja' }],
  },
];

type Elements = ReturnType<typeof buildElements>;

const nodeElements = (elements: Elements) =>
  elements.filter((element) => element.group === 'nodes');
const edgeElements = (elements: Elements) =>
  elements.filter((element) => element.group === 'edges');

const nodes = (elements: Elements) =>
  nodeElements(elements).map((element) => element.data as NodeData);
const edges = (elements: Elements) =>
  edgeElements(elements).map((element) => element.data as EdgeData);

/** `noUncheckedIndexedAccess` is on, so the tests say out loud what they expect. */
function only<T>(items: T[]): T {
  expect(items).toHaveLength(1);
  return items[0] as T;
}

function at<T>(items: T[], index: number): T {
  expect(items.length).toBeGreaterThan(index);
  return items[index] as T;
}

describe('building canvas elements', () => {
  it('makes one node per document and one edge per relation', () => {
    const elements = buildElements(documents);
    expect(nodes(elements).map((node) => node.id)).toEqual([ALICE, ACME]);
    expect(edges(elements)).toHaveLength(1);
  });

  it('labels nodes rather than showing their IRIs', () => {
    expect(nodes(buildElements(documents)).map((node) => node.label)).toEqual([
      '田中太郎',
      '株式会社アクメ',
    ]);
  });

  it('creates a node for a relation target that was not loaded', () => {
    const elements = buildElements([at(documents, 0)]);
    expect(nodes(elements).map((node) => node.id)).toContain(ACME);
  });

  it('marks derived edges so they can be drawn dashed', () => {
    const elements = buildElements(documents, {
      inferredEdges: new Set([edgeId(ALICE, WORKS_FOR, ACME)]),
    });
    expect(only(edges(elements)).inferred).toBe(true);
    expect(only(edgeElements(elements)).classes).toBe('inferred');
  });

  it('marks nodes SHACL flagged so they can be outlined in red', () => {
    const elements = buildElements(documents, { violated: new Set([ALICE]) });
    expect(at(nodes(elements), 0).violated).toBe(true);
  });

  it('keeps the coordinates a node already had, so the canvas does not jump', () => {
    const elements = buildElements(documents, { positions: { [ALICE]: { x: 10, y: 20 } } });
    expect(at(elements, 0).position).toEqual({ x: 10, y: 20 });
    expect(at(elements, 1).position).toBeUndefined();
  });

  it('never emits the same edge twice', () => {
    expect(edges(buildElements([...documents, at(documents, 0)]))).toHaveLength(1);
  });

  it('shortens the predicate for the edge label', () => {
    expect(only(edges(buildElements(documents))).label).toBe('worksFor');
  });

  it('switches to neighbourhood mode past the threshold', () => {
    expect(needsNeighbourhoodMode(NEIGHBOURHOOD_THRESHOLD)).toBe(false);
    expect(needsNeighbourhoodMode(NEIGHBOURHOOD_THRESHOLD + 1)).toBe(true);
  });
});
