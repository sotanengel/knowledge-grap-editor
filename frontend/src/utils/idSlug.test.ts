import { describe, expect, it } from "vitest";
import { slugFromLabel, uniqueId } from "./idSlug";

describe("idSlug", () => {
  it("creates slug from label", () => {
    expect(slugFromLabel("Apple Inc.")).toBe("apple-inc");
    expect(slugFromLabel("山田太郎")).toBe("山田太郎");
  });

  it("returns unique id when duplicate exists", () => {
    const existing = new Set(["apple", "apple-2"]);
    expect(uniqueId("apple", existing)).toBe("apple-3");
  });
});
