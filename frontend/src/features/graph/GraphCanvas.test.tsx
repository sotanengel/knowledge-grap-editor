import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import GraphCanvas from "./GraphCanvas";

vi.mock("cytoscape", () => {
  const makeCollection = () => ({
    forEach: vi.fn(),
    removeClass: vi.fn(),
    unselect: vi.fn(),
  });
  const mockCy = {
    on: vi.fn(),
    add: vi.fn(),
    layout: vi.fn(() => ({ run: vi.fn() })),
    getElementById: vi.fn(() => ({
      empty: vi.fn(() => true),
      nonempty: vi.fn(() => false),
      select: vi.fn(),
      addClass: vi.fn(),
      data: vi.fn(),
      remove: vi.fn(),
    })),
    $: vi.fn(() => ({ unselect: vi.fn() })),
    nodes: vi.fn(() => makeCollection()),
    edges: vi.fn(() => makeCollection()),
    animate: vi.fn(),
    fit: vi.fn(),
    zoom: vi.fn(() => 1),
    center: vi.fn(),
    destroy: vi.fn(),
  };
  return { default: vi.fn(() => mockCy) };
});

describe("GraphCanvas", () => {
  const nodes = [
    { id: "n1", label: "山田太郎", type: "Person", properties: { email: "a@b.com" } },
  ];
  const edges = [
    { id: "e1", subject: "n1", predicate: "worksFor", object: "n2", properties: {} },
  ];

  it("renders graph canvas container", () => {
    render(<GraphCanvas nodes={nodes} edges={edges} />);
    expect(screen.getByTestId("graph-canvas")).toBeInTheDocument();
  });

  it("accepts selection props", () => {
    render(
      <GraphCanvas
        nodes={nodes}
        edges={edges}
        selectedNodeId="n1"
        selectedEdgeId={null}
      />,
    );
    expect(screen.getByTestId("graph-canvas")).toBeInTheDocument();
  });
});
