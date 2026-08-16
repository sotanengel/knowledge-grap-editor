import { useCallback, useEffect, useRef, useState } from "react";
import { api, SuggestResult } from "../api/client";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSelect?: (result: SuggestResult) => void;
  placeholder?: string;
  mode?: "class" | "relationship";
}

function formatDisplay(result: SuggestResult): string {
  if (result.label && result.label !== result.id) {
    return `${result.label} (${result.id})`;
  }
  return result.id;
}

export default function TypeSuggest({
  value,
  onChange,
  onSelect,
  placeholder = "型を入力...",
  mode = "class",
}: Props) {
  const [inputText, setInputText] = useState("");
  const [selected, setSelected] = useState<SuggestResult | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestResult[]>([]);
  const [open, setOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const fetchSuggestions = useCallback(
    async (query: string) => {
      try {
        const res =
          mode === "relationship"
            ? await api.suggestRelationships(query)
            : await api.suggestTypes(query);
        setSuggestions(res.results);
        setHighlightIndex(0);
        setOpen(res.results.length > 0);
      } catch {
        setSuggestions([]);
        setOpen(false);
      }
    },
    [mode],
  );

  useEffect(() => {
    if (!value) {
      setSelected(null);
      setInputText("");
      return;
    }
    if (selected?.id === value) return;
    const suggestFn =
      mode === "relationship" ? api.suggestRelationships : api.suggestTypes;
    void suggestFn(value).then((res) => {
      const match = res.results.find((r) => r.id === value);
      if (match) setSelected(match);
    });
  }, [value, selected?.id, mode]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const displayValue =
    selected && selected.id === value && !inputText ? formatDisplay(selected) : inputText;

  const pick = (s: SuggestResult) => {
    setSelected(s);
    setInputText("");
    onChange(s.id);
    onSelect?.(s);
    setOpen(false);
  };

  const handleInputChange = (text: string) => {
    setInputText(text);
    setSelected(null);
    if (value) onChange("");
    void fetchSuggestions(text);
  };

  const handleFocus = () => {
    void fetchSuggestions(inputText);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open || suggestions.length === 0) {
      if (e.key === "ArrowDown" || e.key === "Enter") {
        void fetchSuggestions(inputText);
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIndex((i) => (i + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIndex((i) => (i - 1 + suggestions.length) % suggestions.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      pick(suggestions[highlightIndex]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className="type-suggest" ref={containerRef}>
      <input
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-autocomplete="list"
        value={displayValue}
        onChange={(e) => handleInputChange(e.target.value)}
        onFocus={handleFocus}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
      />
      {open && suggestions.length > 0 && (
        <ul className="suggest-list" role="listbox">
          {suggestions.map((s, idx) => (
            <li
              key={s.id}
              role="option"
              aria-selected={idx === highlightIndex}
              className={idx === highlightIndex ? "highlighted" : ""}
              onMouseEnter={() => setHighlightIndex(idx)}
              onClick={() => pick(s)}
            >
              <div className="suggest-card-header">
                <strong>{formatDisplay(s)}</strong>
                {s.score > 0 && <span className="score-badge">{Math.round(s.score * 100)}%</span>}
              </div>
              {s.description && <span className="suggest-desc">{s.description}</span>}
              {s.examples && s.examples.length > 0 && (
                <span className="suggest-examples">例: {s.examples.join(", ")}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
