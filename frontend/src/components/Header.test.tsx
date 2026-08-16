import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Header from "./Header";
import { renderWithRouter } from "../test/renderWithRouter";

vi.mock("../api/client");

describe("Header", () => {
  it("highlights active nav link on browse page", () => {
    renderWithRouter(<Header />, { routerProps: { initialEntries: ["/browse"] } });
    const browseLink = screen.getByRole("link", { name: "閲覧" });
    expect(browseLink).toHaveClass("active");
    expect(browseLink).toHaveAttribute("aria-current", "page");
  });

  it("highlights home on root path", () => {
    renderWithRouter(<Header />, { routerProps: { initialEntries: ["/"] } });
    const homeLink = screen.getByRole("link", { name: "ホーム" });
    expect(homeLink).toHaveClass("active");
  });

  it("highlights register on register path", () => {
    renderWithRouter(<Header />, { routerProps: { initialEntries: ["/register"] } });
    const registerLink = screen.getByRole("link", { name: "登録" });
    expect(registerLink).toHaveClass("active");
  });
});
