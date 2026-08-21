/** The literal types the inspector offers (§4.3: a dropdown, never `^^xsd:`). */
export const XSD = 'http://www.w3.org/2001/XMLSchema#';

export interface DatatypeOption {
  value: string;
  label: string;
}

export const DATATYPES: DatatypeOption[] = [
  { value: `${XSD}string`, label: '文字列' },
  { value: `${XSD}integer`, label: '整数' },
  { value: `${XSD}decimal`, label: '小数' },
  { value: `${XSD}boolean`, label: '真偽' },
  { value: `${XSD}date`, label: '日付' },
  { value: `${XSD}dateTime`, label: '日時' },
];

/** What the type dropdown should show for a value already in the graph. */
export function selectedDatatype(datatype?: string, language?: string): string {
  if (language) return 'lang';
  return datatype ?? `${XSD}string`;
}
