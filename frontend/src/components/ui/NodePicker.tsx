import { useMemo, useState } from "react";
import type { Node } from "../../api/client";

interface Props {
  nodes: Node[];
  value: string;
  onChange: (nodeId: string) => void;
  placeholder?: string;
}

export default function NodePicker({ nodes, value, onChange, placeholder = "Nodeを検索..." }: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const selected = nodes.find((n) => n.id === value);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    if (!q) return nodes.slice(0, 20);
    return nodes
      .filter(
        (n) =>
          n.label.toLowerCase().includes(q) ||
          n.id.toLowerCase().includes(q) ||
          n.type.toLowerCase().includes(q),
      )
      .slice(0, 20);
  }, [nodes, query]);

  const display = selected && !query ? selected.label : query;

  return (
    <div className="combobox node-picker">
      <input
        role="combobox"
        aria-expanded={open}
        value={display}
        placeholder={placeholder}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          if (value) onChange("");
        }}
        onFocus={() => setOpen(true)}
      />
      {open && filtered.length > 0 && (
        <ul className="node-picker-list" role="listbox">
          {filtered.map((n) => (
            <li
              key={n.id}
              role="option"
              className={n.id === value ? "selected" : ""}
              onClick={() => {
                onChange(n.id);
                setQuery("");
                setOpen(false);
              }}
            >
              <strong>{n.label}</strong>
              <span>
                {n.type} · {n.id}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
