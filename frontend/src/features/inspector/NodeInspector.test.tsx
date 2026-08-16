import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, resetApiMock } from "../../api/__mocks__/client";
import NodeInspector from "./NodeInspector";

vi.mock("../../api/client");

const node = {
  id: "person-1",
  label: "山田太郎",
  type: "Person",
  properties: { email: "a@example.com", description: "エンジニア" },
};

describe("NodeInspector", () => {
  beforeEach(() => {
    resetApiMock();
  });

  it("displays node details in view mode", () => {
    render(
      <NodeInspector
        node={node}
        nodes={[node]}
        edges={[]}
        onSave={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText("山田太郎")).toBeInTheDocument();
    expect(screen.getByText("person-1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "編集" })).toBeInTheDocument();
  });

  it("shows edit form when edit clicked", async () => {
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
      { id: "email", label: "email", description: "", domain: [], range: [], required: false, aliases: [] },
    ]);
    api.listClasses.mockResolvedValue([
      { id: "Person", label: "Person", description: "", aliases: [], parent_classes: [], examples: [] },
    ]);
    const user = userEvent.setup();
    render(
      <NodeInspector
        node={node}
        nodes={[node]}
        edges={[]}
        onSave={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    await user.click(screen.getByRole("button", { name: "編集" }));
    expect(screen.getByRole("button", { name: "保存" })).toBeInTheDocument();
  });

  it("blocks save when required property missing", async () => {
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
    api.listClasses.mockResolvedValue([
      { id: "Person", label: "Person", description: "", aliases: [], parent_classes: [], examples: [] },
    ]);
    const user = userEvent.setup();
    render(
      <NodeInspector
        node={{ ...node, properties: {} }}
        nodes={[node]}
        edges={[]}
        onSave={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    await user.click(screen.getByRole("button", { name: "編集" }));
    await user.click(screen.getByRole("button", { name: "保存" }));
    await waitFor(() => expect(screen.getByText(/必須/)).toBeInTheDocument());
    expect(api.updateNode).not.toHaveBeenCalled();
  });

  it("shows delete confirmation dialog", async () => {
    const user = userEvent.setup();
    render(
      <NodeInspector
        node={node}
        nodes={[node]}
        edges={[]}
        onSave={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    await user.click(screen.getByRole("button", { name: "削除" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/Relationshipも削除されます/)).toBeInTheDocument();
  });

  it("calls onDelete after confirm", async () => {
    api.deleteNode.mockResolvedValue(undefined);
    const onDelete = vi.fn();
    const user = userEvent.setup();
    render(
      <NodeInspector
        node={node}
        nodes={[node]}
        edges={[]}
        onSave={vi.fn()}
        onDelete={onDelete}
      />,
    );
    await user.click(screen.getByRole("button", { name: "削除" }));
    await user.click(screen.getAllByRole("button", { name: "削除" })[1]);
    await waitFor(() => expect(onDelete).toHaveBeenCalled());
  });
});
