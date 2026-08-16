import type { Edge, Node, OntologyClass, PropertyDef, Relationship } from "../api/client";

export interface ValidationResult {
  valid: boolean;
  fieldErrors: Record<string, string>;
  formError?: string;
}

export interface ValidateNodeOptions {
  existingNodeIds?: Set<string>;
  editingNodeId?: string;
}

export interface ValidateEdgeOptions {
  existingEdges?: Edge[];
  editingEdgeId?: string;
}

const ID_PATTERN = /^[a-z0-9][a-z0-9-_]*$/i;
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

function propertyAppliesToClass(prop: PropertyDef, classId: string): boolean {
  return !prop.domain.length || prop.domain.includes(classId);
}

function inferValueKind(prop: PropertyDef): "date" | "number" | "url" | "boolean" | "text" {
  const range = prop.range.join(" ").toLowerCase();
  if (range.includes("boolean")) return "boolean";
  if (range.includes("integer") || range.includes("decimal") || range.includes("number")) {
    return "number";
  }
  if (range.includes("date")) return "date";
  if (range.includes("uri") || range.includes("url") || range.includes("anyuri")) return "url";
  return "text";
}

function validatePropertyValue(prop: PropertyDef, value: string): string | null {
  if (!value.trim()) return null;
  const kind = inferValueKind(prop);
  switch (kind) {
    case "date":
      if (!ISO_DATE_PATTERN.test(value) || Number.isNaN(Date.parse(value))) {
        return `${prop.label || prop.id} は YYYY-MM-DD 形式の日付で入力してください`;
      }
      return null;
    case "number":
      if (Number.isNaN(Number(value))) {
        return `${prop.label || prop.id} は数値で入力してください`;
      }
      return null;
    case "url":
      try {
        new URL(value);
        return null;
      } catch {
        return `${prop.label || prop.id} は有効な URL で入力してください`;
      }
    case "boolean":
      if (value !== "true" && value !== "false") {
        return `${prop.label || prop.id} は true/false で入力してください`;
      }
      return null;
    default:
      return null;
  }
}

export function validateNode(
  data: { id: string; label: string; type: string; properties: Record<string, string> },
  propertyDefs: PropertyDef[],
  classes: OntologyClass[],
  options: ValidateNodeOptions = {},
): ValidationResult {
  const fieldErrors: Record<string, string> = {};

  if (!data.label.trim()) {
    fieldErrors.label = "名前を入力してください";
  }

  if (!data.type.trim()) {
    fieldErrors.type = "型を選択してください";
  } else if (!classes.some((c) => c.id === data.type)) {
    fieldErrors.type = `型 '${data.type}' はオントロジーに定義されていません`;
  }

  if (!data.id.trim()) {
    fieldErrors.id = "ID を入力してください";
  } else if (!ID_PATTERN.test(data.id)) {
    fieldErrors.id = "ID は英数字・ハイフン・アンダースコアのみ使用できます";
  } else if (
    options.existingNodeIds?.has(data.id) &&
    options.editingNodeId !== data.id
  ) {
    fieldErrors.id = "同じ ID のノードが既に存在します";
  }

  for (const prop of propertyDefs) {
    if (!propertyAppliesToClass(prop, data.type)) continue;
    const value = data.properties[prop.id] ?? "";
    if (prop.required && !value.trim()) {
      fieldErrors[`properties.${prop.id}`] =
        `${prop.label || prop.id} はエディタ必須です（未入力は不明であり、偽ではありません）`;
      continue;
    }
    const formatError = validatePropertyValue(prop, value);
    if (formatError) {
      fieldErrors[`properties.${prop.id}`] = formatError;
    }
  }

  return {
    valid: Object.keys(fieldErrors).length === 0,
    fieldErrors,
  };
}

export function propertyErrorsForForm(
  fieldErrors: Record<string, string>,
): Record<string, string> {
  const mapped: Record<string, string> = {};
  for (const [key, message] of Object.entries(fieldErrors)) {
    if (key.startsWith("properties.")) {
      mapped[key.slice("properties.".length)] = message;
    }
  }
  return mapped;
}

export function validateEdge(
  data: { id?: string; subject: string; predicate: string; object: string },
  relationships: Relationship[],
  nodes: Node[],
  options: ValidateEdgeOptions = {},
): ValidationResult {
  const fieldErrors: Record<string, string> = {};

  if (!data.subject) {
    fieldErrors.subject = "From ノードを選択してください";
  }
  if (!data.predicate) {
    fieldErrors.predicate = "Relationship を選択してください";
  }
  if (!data.object) {
    fieldErrors.object = "To ノードを選択してください";
  }

  const rel = relationships.find((r) => r.id === data.predicate);
  if (data.predicate && !rel) {
    fieldErrors.predicate = `Relationship '${data.predicate}' はオントロジーに定義されていません`;
  }

  const subjectNode = nodes.find((n) => n.id === data.subject);
  const objectNode = nodes.find((n) => n.id === data.object);

  if (data.subject && !subjectNode) {
    fieldErrors.subject = `Subject ノード '${data.subject}' が存在しません`;
  }
  if (data.object && !objectNode) {
    fieldErrors.object = `Object ノード '${data.object}' が存在しません`;
  }

  if (data.subject && data.object && data.subject === data.object) {
    fieldErrors.object = "自分自身への Relationship は作成できません";
  }

  if (rel && subjectNode && rel.domain.length && !rel.domain.includes(subjectNode.type)) {
    fieldErrors.predicate = `'${data.predicate}' の domain は ${rel.domain.join(", ")} です`;
  }

  if (rel && objectNode && rel.range.length && !rel.range.includes(objectNode.type)) {
    fieldErrors.predicate = `'${data.predicate}' の range は ${rel.range.join(", ")} です`;
  }

  let formError: string | undefined;
  if (options.existingEdges && data.subject && data.predicate && data.object) {
    const duplicate = options.existingEdges.some(
      (e) =>
        e.id !== options.editingEdgeId &&
        e.subject === data.subject &&
        e.predicate === data.predicate &&
        e.object === data.object,
    );
    if (duplicate) {
      formError = "同じ Relationship が既に存在します";
    }
  }

  const valid = Object.keys(fieldErrors).length === 0 && !formError;
  return { valid, fieldErrors, formError };
}

export function filterRelationshipsByNodes(
  sourceNode: Node,
  targetNode: Node,
  relationships: Relationship[],
): Relationship[] {
  return relationships.filter((rel) => {
    const domainOk = !rel.domain.length || rel.domain.includes(sourceNode.type);
    const rangeOk = !rel.range.length || rel.range.includes(targetNode.type);
    return domainOk && rangeOk;
  });
}
