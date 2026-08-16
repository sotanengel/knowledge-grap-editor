import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import RegisterPage from "./RegisterPage";

vi.mock("../components/RegisterNodeWizard", () => ({
  default: () => <div data-testid="node-wizard">Node Wizard</div>,
}));

vi.mock("../components/RegisterEdgeWizard", () => ({
  default: () => <div data-testid="edge-wizard">Edge Wizard</div>,
}));

describe("RegisterPage", () => {
  it("shows choose screen initially", () => {
    render(<RegisterPage />);
    expect(screen.getByText("登録するものを選ぶ")).toBeInTheDocument();
  });

  it("opens node wizard when node card clicked", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);
    await user.click(screen.getByRole("button", { name: /ノードを登録/ }));
    expect(screen.getByTestId("node-wizard")).toBeInTheDocument();
  });

  it("opens edge wizard when edge card clicked", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);
    await user.click(screen.getByRole("button", { name: /関係を登録/ }));
    expect(screen.getByTestId("edge-wizard")).toBeInTheDocument();
  });
});
