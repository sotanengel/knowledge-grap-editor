import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import { renderWithRouter } from "./test/renderWithRouter";

vi.mock("./components/GraphCanvas", () => ({
  default: () => <div data-testid="graph-canvas-mock">Graph</div>,
}));

vi.mock("./api/client");

describe("App", () => {
  it("renders header navigation", () => {
    renderWithRouter(<App />);
    expect(screen.getByText("ナレッジグラフ")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "ホーム" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "閲覧" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "登録" })).toBeInTheDocument();
  });

  it("shows browse page with search", async () => {
    renderWithRouter(<App />, { routerProps: { initialEntries: ["/browse"] } });
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "検索" })).toBeInTheDocument();
    });
  });

  it("shows register page", () => {
    renderWithRouter(<App />, { routerProps: { initialEntries: ["/register"] } });
    expect(screen.getByText("登録するものを選ぶ")).toBeInTheDocument();
  });
});
