import { describe, expect, it } from "vitest";
import { graphSignature } from "./graphSync";

describe("graphSignature", () => {
  const nodes = [{ id: "n1", label: "A", type: "Person", properties: {} }];
  const edges = [{ id: "e1", subject: "n1", predicate: "knows", object: "n2", properties: {} }];

  it("returns same signature for identical graph", () => {
    expect(graphSignature(nodes, edges)).toBe(graphSignature([...nodes], [...edges]));
  });

  it("returns different signature when nodes change", () => {
    const sig1 = graphSignature(nodes, edges);
    const sig2 = graphSignature([{ ...nodes[0], label: "B" }], edges);
    expect(sig1).not.toBe(sig2);
  });
});
