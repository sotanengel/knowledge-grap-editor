/** Just enough CSV reading to preview a file and offer its columns (FR-13). */
export interface Preview {
  header: string[];
  rows: string[][];
}

/** Parse a delimited file, honouring quoted fields and embedded newlines. */
export function parseDelimited(text: string, delimiter = ','): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = '';
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];

    if (quoted) {
      if (character === '"') {
        if (text[index + 1] === '"') {
          field += '"';
          index += 1;
        } else {
          quoted = false;
        }
      } else {
        field += character;
      }
      continue;
    }

    if (character === '"') {
      quoted = true;
    } else if (character === delimiter) {
      row.push(field);
      field = '';
    } else if (character === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else if (character !== '\r') {
      field += character;
    }
  }

  if (field !== '' || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows.filter((entry) => entry.some((cell) => cell !== ''));
}

export function preview(text: string, delimiter = ',', limit = 5): Preview {
  const [header = [], ...rest] = parseDelimited(text, delimiter);
  return { header, rows: rest.slice(0, limit) };
}

/** Tabs win when the first line has more of them than commas. */
export function guessDelimiter(text: string): string {
  const [line = ''] = text.split('\n');
  return (line.match(/\t/g) ?? []).length > (line.match(/,/g) ?? []).length ? '\t' : ',';
}
