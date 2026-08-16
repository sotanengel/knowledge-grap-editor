import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./components/GraphCanvas", () => ({
  default: () => <div data-testid="graph-canvas-mock">Graph</div>,
}));

vi.mock("./api/client", () => ({
  api: {
    listNodes: vi.fn().mockResolvedValue([]),
    listEdges: vi.fn().mockResolvedValue([]),
    listClasses: vi.fn().mockResolvedValue([
      { id: "Organization", label: "組織", description: "", aliases: [], parent_classes: [], examples: [] },
    ]),
    listRelationships: vi.fn().mockResolvedValue([]),
    searchGraph: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
    getNeighbors: vi.fn().mockResolvedValue({ nodes: [], edges: [], center: null, depth: 1 }),
    exportRdf: vi.fn(),
    suggestTypes: vi.fn().mockResolvedValue({ results: [] }),
    suggestRelationships: vi.fn().mockResolvedValue({ results: [] }),
    getClassProperties: vi.fn().mockResolvedValue([]),
  },
}));

function renderApp(initialRoute = "/") {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App", () => {
  it("renders header navigation", async () => {
    renderApp();
    expect(screen.getByText("ナレッジグラフ")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "ホーム" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "閲覧" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "登録" })).toBeInTheDocument();
  });

  it("shows browse page with search", async () => {
    renderApp("/browse");
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "検索" })).toBeInTheDocument();
    });
  });

  it("shows register page", async () => {
    renderApp("/register");
    expect(screen.getByText("登録するものを選ぶ")).toBeInTheDocument();
  });
});
