import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, resetApiMock } from "../../api/__mocks__/client";
import { ToastProvider } from "../../components/ui/ToastProvider";
import EdgeCreateForm from "./EdgeCreateForm";

vi.mock("../../api/client");

const nodes = [
  { id: "p1", label: "Person1", type: "Person", properties: {} },
  { id: "prod1", label: "Product1", type: "Product", properties: {} },
  { id: "o1", label: "Org1", type: "Organization", properties: {} },
];

async function pickNode(user: ReturnType<typeof userEvent.setup>, fieldLabel: string, nodeLabel: string) {
  const field = screen.getByText(fieldLabel).closest("label")!;
  const input = field.querySelector('[role="combobox"]')!;
  await user.click(input);
  const listbox = field.querySelector('[role="listbox"]')!;
  await user.click(within(listbox as HTMLElement).getByText(nodeLabel));
}

describe("EdgeCreateForm", () => {
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

  it("blocks submit when node pair has no valid relationship", async () => {
    const user = userEvent.setup();
    render(
      <ToastProvider>
        <EdgeCreateForm nodes={nodes} onCreated={vi.fn()} onCancel={vi.fn()} />
      </ToastProvider>,
    );
    await pickNode(user, "From", "Product1");
    await pickNode(user, "To", "Org1");
    await user.click(screen.getByRole("button", { name: "作成" }));
    await waitFor(() => expect(screen.getByText(/Relationship を選択/)).toBeInTheDocument());
    expect(api.createEdge).not.toHaveBeenCalled();
  });
});
