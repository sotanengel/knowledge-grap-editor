export const NAME_PROPERTY = "name";

export function resolveNodeLabel(node: {
  label: string;
  properties: Record<string, string>;
}): string {
  const name = node.properties[NAME_PROPERTY]?.trim();
  if (name) return name;
  return node.label.trim();
}

export function nodePropertiesWithLabel(
  label: string,
  properties: Record<string, string>,
): Record<string, string> {
  if (properties[NAME_PROPERTY]?.trim()) return properties;
  if (!label.trim()) return properties;
  return { ...properties, [NAME_PROPERTY]: label.trim() };
}
