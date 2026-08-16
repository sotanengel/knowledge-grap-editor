import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import { renderWithRouter } from "./test/renderWithRouter";

vi.mock("./features/graph/GraphCanvas", () => ({
  default: () => <div data-testid="graph-canvas-mock">Graph</div>,
}));

vi.mock("./api/client");

describe("App", () => {
  it("renders header navigation with graph, search, ontology", () => {
    renderWithRouter(<App />);
    expect(screen.getByText("ナレッジグラフ")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "グラフ" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "検索" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "オントロジー" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "ホーム" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "登録" })).not.toBeInTheDocument();
  });

  it("shows graph page with three-column layout", async () => {
    renderWithRouter(<App />, { routerProps: { initialEntries: ["/"] } });
    await waitFor(() => {
      expect(screen.getByTestId("pane-left")).toBeInTheDocument();
      expect(screen.getByTestId("pane-center")).toBeInTheDocument();
      expect(screen.getByTestId("pane-right")).toBeInTheDocument();
    });
  });

  it("shows search page", () => {
    renderWithRouter(<App />, { routerProps: { initialEntries: ["/search"] } });
    expect(screen.getByRole("heading", { name: "検索" })).toBeInTheDocument();
  });

  it("shows ontology page", () => {
    renderWithRouter(<App />, { routerProps: { initialEntries: ["/ontology"] } });
    expect(screen.getByRole("heading", { name: "オントロジー" })).toBeInTheDocument();
  });

  it("redirects /browse to graph page", async () => {
    renderWithRouter(<App />, { routerProps: { initialEntries: ["/browse"] } });
    await waitFor(() => {
      expect(screen.getByTestId("pane-center")).toBeInTheDocument();
    });
  });
});
