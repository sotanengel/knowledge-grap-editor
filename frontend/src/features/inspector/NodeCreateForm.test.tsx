import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, resetApiMock } from "../../api/__mocks__/client";
import { ToastProvider } from "../../components/ui/ToastProvider";
import NodeCreateForm from "./NodeCreateForm";

vi.mock("../../api/client");

function renderForm(props: Partial<Parameters<typeof NodeCreateForm>[0]> = {}) {
  const onCreated = vi.fn();
  const onCancel = vi.fn();
  render(
    <ToastProvider>
      <NodeCreateForm onCreated={onCreated} onCancel={onCancel} {...props} />
    </ToastProvider>,
  );
  return { onCreated, onCancel };
}

describe("NodeCreateForm", () => {
  beforeEach(() => {
    resetApiMock();
    vi.clearAllMocks();
    api.listNodes.mockResolvedValue([]);
    api.listClasses.mockResolvedValue([
      { id: "Person", label: "Person", description: "", aliases: [], parent_classes: [], examples: [] },
    ]);
    api.suggestTypes.mockResolvedValue({
      results: [{ id: "Person", label: "人物", description: "", score: 1 }],
    });
    api.getClassProperties.mockResolvedValue([
      {
        id: "birthDate",
        label: "birthDate",
        description: "",
        domain: ["Person"],
        range: ["xsd:date"],
        required: true,
        aliases: [],
      },
    ]);
  });

  it("creates node on submit when valid", async () => {
    api.createNode.mockResolvedValue({
      id: "yamada",
      label: "山田太郎",
      type: "Person",
      properties: { birthDate: "1990-01-01" },
    });
    const user = userEvent.setup();
    const { onCreated } = renderForm();
    await user.type(screen.getByLabelText("名前"), "山田太郎");
    await user.click(screen.getByRole("combobox"));
    await waitFor(() => screen.getByText("Person"));
    await user.click(screen.getByText("Person"));
    await user.type(screen.getByLabelText(/birthDate/), "1990-01-01");
    await user.click(screen.getByRole("button", { name: "作成" }));
    await waitFor(() => expect(api.createNode).toHaveBeenCalled());
    expect(onCreated).toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent("Nodeを作成しました");
  });

  it("blocks submit when required property is missing", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.type(screen.getByLabelText("名前"), "山田太郎");
    await user.click(screen.getByRole("combobox"));
    await waitFor(() => screen.getByText("Person"));
    await user.click(screen.getByText("Person"));
    await waitFor(() => screen.getByLabelText(/birthDate/));
    await user.click(screen.getByRole("button", { name: "作成" }));
    await waitFor(() => expect(screen.getByText(/必須/)).toBeInTheDocument());
    expect(api.createNode).not.toHaveBeenCalled();
  });
});
