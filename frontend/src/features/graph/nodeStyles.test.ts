import { describe, expect, it } from "vitest";
import {
  buildCytoscapeStyles,
  buildNodeLabel,
  getTypeDisplayLabel,
  getTypeIcon,
  LAYOUT_OPTIONS,
} from "./nodeStyles";

describe("nodeStyles", () => {
  it("returns icon for known types", () => {
    expect(getTypeIcon("Person")).toBe("👤");
    expect(getTypeIcon("Organization")).toBe("🏢");
  });

  it("returns fallback icon for unknown types", () => {
    expect(getTypeIcon("UnknownType")).toBe("◆");
  });

  it("builds type display label with icon and name", () => {
    expect(getTypeDisplayLabel("Person")).toBe("👤 Person");
  });

  it("builds multi-line node label", () => {
    const label = buildNodeLabel("Person", "山田太郎", "example@example.com");
    expect(label).toContain("👤 Person");
    expect(label).toContain("山田太郎");
    expect(label).toContain("example@example.com");
  });

  it("builds cytoscape styles with type-specific selectors", () => {
    const styles = buildCytoscapeStyles();
    expect(styles.length).toBeGreaterThan(5);
    expect(styles[0].selector).toBe("node");
    const personStyle = styles.find((s) => s.selector === 'node[type = "Person"]');
    expect(personStyle).toBeDefined();
  });

  it("provides layout options", () => {
    expect(LAYOUT_OPTIONS.force.name).toBe("cose");
    expect(LAYOUT_OPTIONS.hierarchical.name).toBe("breadthfirst");
    expect(LAYOUT_OPTIONS.radial.name).toBe("concentric");
  });
});
