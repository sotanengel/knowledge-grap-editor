import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, resetApiMock } from "../api/__mocks__/client";
import { ToastProvider } from "../components/ui/ToastProvider";
import GraphPage from "./GraphPage";
import { renderWithRouter } from "../test/renderWithRouter";

vi.mock("../api/client");
vi.mock("../features/graph/GraphCanvas", () => ({
  default: vi.fn(() => <div data-testid="graph-canvas-mock">Graph</div>),
}));

function renderGraphPage() {
  return renderWithRouter(
    <ToastProvider>
      <GraphPage />
    </ToastProvider>,
  );
}

describe("GraphPage", () => {
  beforeEach(() => {
    resetApiMock();
  });

  it("shows node create form when + Node clicked", async () => {
    const user = userEvent.setup();
    renderGraphPage();
    await waitFor(() => expect(api.listNodes).toHaveBeenCalled());
    await user.click(screen.getByRole("button", { name: "+ Node" }));
    expect(screen.getByTestId("node-create-form")).toBeInTheDocument();
  });
});
