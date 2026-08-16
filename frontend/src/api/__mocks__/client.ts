import { vi } from "vitest";

export const api = {
  health: vi.fn().mockResolvedValue({ status: "ok" }),
  listNodes: vi.fn().mockResolvedValue([]),
  listEdges: vi.fn().mockResolvedValue([]),
  listClasses: vi.fn().mockResolvedValue([]),
  listRelationships: vi.fn().mockResolvedValue([]),
  searchGraph: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
  getNeighbors: vi.fn().mockResolvedValue({ nodes: [], edges: [], center: null, depth: 1 }),
  getClassProperties: vi.fn().mockResolvedValue([]),
  createNode: vi.fn().mockResolvedValue({ id: "n1", label: "Test", type: "Person", properties: {} }),
  createEdge: vi.fn().mockResolvedValue({
    id: "e1",
    subject: "a",
    predicate: "worksFor",
    object: "b",
    properties: {},
  }),
  suggestTypes: vi.fn().mockResolvedValue({ results: [] }),
  suggestRelationships: vi.fn().mockResolvedValue({ results: [] }),
  exportRdf: vi.fn(),
};

export function resetApiMock() {
  api.health.mockResolvedValue({ status: "ok" });
  api.listNodes.mockResolvedValue([]);
  api.listEdges.mockResolvedValue([]);
  api.listClasses.mockResolvedValue([]);
  api.listRelationships.mockResolvedValue([]);
  api.searchGraph.mockResolvedValue({ nodes: [], edges: [] });
  api.getNeighbors.mockResolvedValue({ nodes: [], edges: [], center: null, depth: 1 });
  api.getClassProperties.mockResolvedValue([]);
  api.createNode.mockResolvedValue({ id: "n1", label: "Test", type: "Person", properties: {} });
  api.createEdge.mockResolvedValue({
    id: "e1",
    subject: "a",
    predicate: "worksFor",
    object: "b",
    properties: {},
  });
  api.suggestTypes.mockResolvedValue({ results: [] });
  api.suggestRelationships.mockResolvedValue({ results: [] });
}
