import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./components/GraphCanvas", () => ({
  default: () => <div data-testid="graph-canvas-mock">Graph</div>,
}));

vi.mock("./api/client", () => ({
  api: {
    listNodes: vi.fn().mockResolvedValue([]),
    listEdges: vi.fn().mockResolvedValue([]),
    listClasses: vi.fn().mockResolvedValue([]),
    listRelationships: vi.fn().mockResolvedValue([]),
    searchGraph: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
    getNeighbors: vi.fn().mockResolvedValue({ nodes: [], edges: [], center: null, depth: 1 }),
    exportRdf: vi.fn(),
    suggestTypes: vi.fn().mockResolvedValue({ results: [] }),
    suggestRelationships: vi.fn().mockResolvedValue({ results: [] }),
  },
}));

describe("App", () => {
  it("renders title", async () => {
    render(<App />);
    expect(screen.getByText("ナレッジグラフ")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "検索" })).toBeInTheDocument();
  });
});
