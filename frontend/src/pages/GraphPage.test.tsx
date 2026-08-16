import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, resetApiMock } from "../api/__mocks__/client";
import { ToastProvider } from "../components/ui/ToastProvider";
import GraphPage from "./GraphPage";
import { renderWithRouter } from "../test/renderWithRouter";

vi.mock("../api/client");

let connectHandler: ((sourceId: string, targetId: string) => void) | undefined;

vi.mock("../features/graph/GraphCanvas", () => ({
  default: vi.fn((props: { onConnectRequest?: (sourceId: string, targetId: string) => void }) => {
    connectHandler = props.onConnectRequest;
    return (
      <div data-testid="graph-canvas-mock">
        Graph
        <button
          type="button"
          onClick={() => connectHandler?.("p1", "o1")}
        >
          Simulate connect
        </button>
      </div>
    );
  }),
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
    api.listRelationships.mockResolvedValue([
      {
        id: "worksFor",
        label: "works for",
        description: "",
        domain: ["Person"],
        range: ["Organization"],
        aliases: [],
      },
    ]);
    api.suggestRelationships.mockResolvedValue({
      results: [{ id: "worksFor", label: "works for", description: "", score: 1 }],
    });
  });

  it("shows node create form when + Node clicked", async () => {
    const user = userEvent.setup();
    renderGraphPage();
    await waitFor(() => expect(api.listNodes).toHaveBeenCalled());
    await user.click(screen.getByRole("button", { name: "+ Node" }));
    expect(screen.getByTestId("node-create-form")).toBeInTheDocument();
  });

  it("opens relationship picker on canvas connect", async () => {
    api.listNodes.mockResolvedValue([
      { id: "p1", label: "Person1", type: "Person", properties: {} },
      { id: "o1", label: "Org1", type: "Organization", properties: {} },
    ]);
    const user = userEvent.setup();
    renderGraphPage();
    await waitFor(() => expect(api.listNodes).toHaveBeenCalled());
    await user.click(screen.getByRole("button", { name: "Simulate connect" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/Person1/)).toBeInTheDocument();
  });
});
