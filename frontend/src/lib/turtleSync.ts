/**
 * Two-way Turtle sync (FR-09).
 *
 * Saving replaces the data graph with what is in the editor. That is done as a
 * single SPARQL Update — one change log entry, one undo step — rather than as a
 * stream of small edits, so a bad paste is one keystroke away from being undone.
 *
 * Parse errors from the server carry a line number; `parseErrorLine` digs it out
 * so the editor can point at the offending line rather than saying "invalid".
 */
export const DATA_GRAPH = 'urn:ontoforge:data';

/** The Update that makes the data graph exactly `turtle`. */
export function buildReplaceUpdate(turtle: string, graph = DATA_GRAPH): string {
  return `DROP SILENT GRAPH <${graph}> ;\nINSERT DATA {\n  GRAPH <${graph}> {\n${indent(turtle)}\n  }\n}`;
}

function indent(text: string): string {
  return text
    .split('\n')
    .filter((line) => !/^\s*@(prefix|base)\b/i.test(line))
    .map((line) => (line.trim() ? `    ${line}` : ''))
    .join('\n');
}

/** Prefix declarations have to move above the Update, not inside the data block. */
export function extractPrefixes(turtle: string): string {
  return turtle
    .split('\n')
    .filter((line) => /^\s*@(prefix|base)\b/i.test(line))
    .map((line) =>
      line
        .trim()
        .replace(/^@prefix/i, 'PREFIX')
        .replace(/^@base/i, 'BASE')
        .replace(/\s*\.\s*$/, ''),
    )
    .join('\n');
}

export function buildUpdate(turtle: string, graph = DATA_GRAPH): string {
  const prefixes = extractPrefixes(turtle);
  const body = buildReplaceUpdate(turtle, graph);
  return prefixes ? `${prefixes}\n${body}` : body;
}

/** The 1-based line a parser complained about, if the message names one. */
export function parseErrorLine(message: string): number | null {
  const match =
    /line (\d+)/i.exec(message) ?? /at line (\d+)/i.exec(message) ?? /:(\d+):\d+/.exec(message);
  if (!match) return null;
  const line = Number(match[1]);
  return Number.isFinite(line) && line > 0 ? line : null;
}
