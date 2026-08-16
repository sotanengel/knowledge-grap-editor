import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import EdgeInspector from "./EdgeInspector";

const nodes = [
  { id: "n1", label: "山田太郎", type: "Person", properties: {} },
  { id: "n2", label: "株式会社ABC", type: "Organization", properties: {} },
];

const edge = {
  id: "e1",
  subject: "n1",
  predicate: "worksFor",
  object: "n2",
  properties: { startDate: "2025-01-01" },
};

describe("EdgeInspector", () => {
  it("displays edge from and to labels", () => {
    render(
      <EdgeInspector
        edge={edge}
        nodes={nodes}
        onSave={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText("worksFor")).toBeInTheDocument();
    expect(screen.getByText("山田太郎")).toBeInTheDocument();
    expect(screen.getByText("株式会社ABC")).toBeInTheDocument();
  });
});
