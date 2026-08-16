import { useEffect, useState } from "react";
import { api, SuggestResult } from "../api/client";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSelect?: (result: SuggestResult) => void;
  placeholder?: string;
  mode?: "class" | "relationship";
}

export default function TypeSuggest({
  value,
  onChange,
  onSelect,
  placeholder = "型を入力...",
  mode = "class",
}: Props) {
  const [suggestions, setSuggestions] = useState<SuggestResult[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!value.trim()) {
      setSuggestions([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res =
          mode === "relationship"
            ? await api.suggestRelationships(value)
            : await api.suggestTypes(value);
        setSuggestions(res.results);
        setOpen(res.results.length > 0);
      } catch {
        setSuggestions([]);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [value, mode]);

  return (
    <div className="type-suggest">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        onFocus={() => setOpen(suggestions.length > 0)}
      />
      {open && suggestions.length > 0 && (
        <ul className="suggest-list">
          {suggestions.map((s) => (
            <li
              key={s.id}
              onClick={() => {
                onChange(s.id);
                onSelect?.(s);
                setOpen(false);
              }}
            >
              <strong>{s.label}</strong>
              <span>{s.description}</span>
              <span className="score">類似度: {s.score}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
