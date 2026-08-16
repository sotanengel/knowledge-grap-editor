import { describe, expect, it } from "vitest";
import type { Edge, Node, OntologyClass, PropertyDef, Relationship } from "../api/client";
import {
  filterRelationshipsByNodes,
  validateEdge,
  validateNode,
} from "./graphValidation";

const classes: OntologyClass[] = [
  { id: "Person", label: "Person", description: "", aliases: [], parent_classes: [], examples: [] },
  {
    id: "Organization",
    label: "Organization",
    description: "",
    aliases: [],
    parent_classes: [],
    examples: [],
  },
  { id: "Product", label: "Product", description: "", aliases: [], parent_classes: [], examples: [] },
];

const personProps: PropertyDef[] = [
  {
    id: "name",
    label: "name",
    description: "",
    domain: [],
    range: ["xsd:string"],
    required: false,
    aliases: [],
  },
  {
    id: "birthDate",
    label: "birthDate",
    description: "",
    domain: ["Person"],
    range: ["xsd:date"],
    required: true,
    aliases: [],
  },
  {
    id: "email",
    label: "email",
    description: "",
    domain: ["Person"],
    range: ["xsd:string"],
    required: false,
    aliases: [],
  },
];

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

const nodes: Node[] = [
  { id: "p1", label: "Person1", type: "Person", properties: {} },
  { id: "o1", label: "Org1", type: "Organization", properties: {} },
  { id: "prod1", label: "Product1", type: "Product", properties: {} },
];

describe("validateNode", () => {
  it("requires name property and type", () => {
    const result = validateNode(
      { id: "x", label: "", type: "", properties: { name: "  " } },
      personProps,
      classes,
    );
    expect(result.valid).toBe(false);
    expect(result.fieldErrors["properties.name"]).toBeTruthy();
    expect(result.fieldErrors.type).toBeTruthy();
  });

  it("rejects invalid node type", () => {
    const result = validateNode(
      { id: "x", label: "Test", type: "UnknownType", properties: {} },
      personProps,
      classes,
    );
    expect(result.valid).toBe(false);
    expect(result.fieldErrors.type).toMatch(/オントロジー/);
  });

  it("requires birthDate for Person", () => {
    const result = validateNode(
      { id: "p2", label: "山田", type: "Person", properties: { name: "山田" } },
      personProps,
      classes,
    );
    expect(result.valid).toBe(false);
    expect(result.fieldErrors["properties.birthDate"]).toBeTruthy();
  });

  it("rejects invalid date format", () => {
    const result = validateNode(
      {
        id: "p2",
        label: "山田",
        type: "Person",
        properties: { name: "山田", birthDate: "not-a-date" },
      },
      personProps,
      classes,
    );
    expect(result.valid).toBe(false);
    expect(result.fieldErrors["properties.birthDate"]).toMatch(/日付/);
  });

  it("accepts valid Person node", () => {
    const result = validateNode(
      {
        id: "p2",
        label: "山田",
        type: "Person",
        properties: { name: "山田", birthDate: "1990-01-15" },
      },
      personProps,
      classes,
    );
    expect(result.valid).toBe(true);
  });

  it("rejects duplicate id on create", () => {
    const result = validateNode(
      {
        id: "p1",
        label: "Dup",
        type: "Person",
        properties: { name: "Dup", birthDate: "1990-01-15" },
      },
      personProps,
      classes,
      { existingNodeIds: new Set(["p1"]) },
    );
    expect(result.valid).toBe(false);
    expect(result.fieldErrors.id).toMatch(/既に/);
  });

  it("rejects invalid id format", () => {
    const result = validateNode(
      {
        id: "bad id!",
        label: "Test",
        type: "Person",
        properties: { name: "Test", birthDate: "1990-01-15" },
      },
      personProps,
      classes,
    );
    expect(result.valid).toBe(false);
    expect(result.fieldErrors.id).toBeTruthy();
  });
});

describe("validateEdge", () => {
  it("requires subject, predicate, object", () => {
    const result = validateEdge({ subject: "", predicate: "", object: "" }, relationships, nodes);
    expect(result.valid).toBe(false);
  });

  it("rejects domain violation", () => {
    const result = validateEdge(
      { subject: "prod1", predicate: "worksFor", object: "o1" },
      relationships,
      nodes,
    );
    expect(result.valid).toBe(false);
    expect(result.fieldErrors.predicate).toMatch(/domain/);
  });

  it("accepts valid edge", () => {
    const result = validateEdge(
      { subject: "p1", predicate: "worksFor", object: "o1" },
      relationships,
      nodes,
    );
    expect(result.valid).toBe(true);
  });

  it("rejects self-loop", () => {
    const result = validateEdge(
      { subject: "p1", predicate: "worksFor", object: "p1" },
      relationships,
      nodes,
    );
    expect(result.valid).toBe(false);
    expect(result.fieldErrors.object).toMatch(/自分自身/);
  });

  it("rejects duplicate edge", () => {
    const existing: Edge[] = [
      { id: "e1", subject: "p1", predicate: "worksFor", object: "o1", properties: {} },
    ];
    const result = validateEdge(
      { subject: "p1", predicate: "worksFor", object: "o1" },
      relationships,
      nodes,
      { existingEdges: existing },
    );
    expect(result.valid).toBe(false);
    expect(result.formError).toMatch(/既に/);
  });
});

describe("filterRelationshipsByNodes", () => {
  it("returns worksFor for Person to Organization", () => {
    const filtered = filterRelationshipsByNodes(nodes[0], nodes[1], relationships);
    expect(filtered.map((r) => r.id)).toEqual(["worksFor"]);
  });

  it("returns produces for Organization to Product", () => {
    const filtered = filterRelationshipsByNodes(nodes[1], nodes[2], relationships);
    expect(filtered.map((r) => r.id)).toEqual(["produces"]);
  });

  it("returns empty for incompatible types", () => {
    const filtered = filterRelationshipsByNodes(nodes[2], nodes[0], relationships);
    expect(filtered).toHaveLength(0);
  });
});
