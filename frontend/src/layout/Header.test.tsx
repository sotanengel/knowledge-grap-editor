import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Header from "./Header";
import { renderWithRouter } from "../test/renderWithRouter";

vi.mock("../api/client");

describe("Header", () => {
  it("highlights graph nav on root path", () => {
    renderWithRouter(<Header />, { routerProps: { initialEntries: ["/"] } });
    const graphLink = screen.getByRole("link", { name: "グラフ" });
    expect(graphLink).toHaveClass("active");
    expect(graphLink).toHaveAttribute("aria-current", "page");
  });

  it("highlights search on search path", () => {
    renderWithRouter(<Header />, { routerProps: { initialEntries: ["/search"] } });
    const searchLink = screen.getByRole("link", { name: "検索" });
    expect(searchLink).toHaveClass("active");
  });

  it("highlights ontology on ontology path", () => {
    renderWithRouter(<Header />, { routerProps: { initialEntries: ["/ontology"] } });
    const ontologyLink = screen.getByRole("link", { name: "オントロジー" });
    expect(ontologyLink).toHaveClass("active");
  });
});
