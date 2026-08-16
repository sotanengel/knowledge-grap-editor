import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import type { Node, Relationship } from "../../api/client";
import { api, resetApiMock } from "../../api/__mocks__/client";
import RelationshipPickerDialog from "./RelationshipPickerDialog";

vi.mock("../../api/client");

const sourceNode: Node = { id: "p1", label: "Person1", type: "Person", properties: {} };
const targetNode: Node = { id: "o1", label: "Org1", type: "Organization", properties: {} };

const relationships: Relationship[] = [
  {
    id: "worksFor",
    label: "works for",
    description: "",
    domain: ["Person"],
    range: ["Organization"],
    aliases: [],
  },
  {
    id: "produces",
    label: "produces",
    description: "",
    domain: ["Organization"],
    range: ["Product"],
    aliases: [],
  },
];

describe("RelationshipPickerDialog", () => {
  beforeEach(() => {
    resetApiMock();
    api.suggestRelationships.mockResolvedValue({
      results: [{ id: "worksFor", label: "works for", description: "", score: 1 }],
    });
  });

  it("shows compatible relationships and confirms selection", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    const user = userEvent.setup();

    render(
      <RelationshipPickerDialog
        open
        sourceNode={sourceNode}
        targetNode={targetNode}
        relationships={relationships}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/Person1/)).toBeInTheDocument();
    expect(screen.getByText(/Org1/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "作成" }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledWith("worksFor"));
  });

  it("shows error when no compatible relationships", () => {
    render(
      <RelationshipPickerDialog
        open
        sourceNode={{ id: "prod1", label: "Product1", type: "Product", properties: {} }}
        targetNode={sourceNode}
        relationships={relationships}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByText(/使用できる Relationship がありません/)).toBeInTheDocument();
  });

  it("calls onCancel", async () => {
    const onCancel = vi.fn();
    const user = userEvent.setup();
    render(
      <RelationshipPickerDialog
        open
        sourceNode={sourceNode}
        targetNode={targetNode}
        relationships={relationships}
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    );
    await user.click(screen.getByRole("button", { name: "キャンセル" }));
    expect(onCancel).toHaveBeenCalled();
  });
});
