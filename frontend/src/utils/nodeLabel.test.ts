import { describe, expect, it } from "vitest";
import {
  NAME_PROPERTY,
  nodePropertiesWithLabel,
  resolveNodeLabel,
} from "./nodeLabel";

describe("resolveNodeLabel", () => {
  it("prefers properties.name over label", () => {
    expect(
      resolveNodeLabel({
        label: "旧ラベル",
        properties: { [NAME_PROPERTY]: "新しい名前" },
      }),
    ).toBe("新しい名前");
  });

  it("falls back to label when name property is empty", () => {
    expect(
      resolveNodeLabel({
        label: "山田太郎",
        properties: {},
      }),
    ).toBe("山田太郎");
  });
});

describe("nodePropertiesWithLabel", () => {
  it("fills name from label when missing", () => {
    expect(nodePropertiesWithLabel("山田太郎", { email: "a@b.com" })).toEqual({
      email: "a@b.com",
      [NAME_PROPERTY]: "山田太郎",
    });
  });

  it("keeps existing name property", () => {
    expect(nodePropertiesWithLabel("旧ラベル", { [NAME_PROPERTY]: "正式名称" })).toEqual({
      [NAME_PROPERTY]: "正式名称",
    });
  });
});
