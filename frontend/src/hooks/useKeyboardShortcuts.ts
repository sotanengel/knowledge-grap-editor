import { useEffect } from "react";

interface ShortcutHandlers {
  onAddNode?: () => void;
  onAddEdge?: () => void;
  onDelete?: () => void;
  onEscape?: () => void;
  onSearch?: () => void;
  onSave?: () => void;
}

export function useKeyboardShortcuts(handlers: ShortcutHandlers) {
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT") {
        if (e.key === "Escape") handlers.onEscape?.();
        return;
      }

      if (e.key === "n" || e.key === "N") {
        if (!e.metaKey && !e.ctrlKey) handlers.onAddNode?.();
      } else if (e.key === "e" || e.key === "E") {
        if (!e.metaKey && !e.ctrlKey) handlers.onAddEdge?.();
      } else if (e.key === "Delete" || e.key === "Backspace") {
        handlers.onDelete?.();
      } else if (e.key === "Escape") {
        handlers.onEscape?.();
      } else if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        handlers.onSearch?.();
      } else if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        handlers.onSave?.();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handlers]);
}
