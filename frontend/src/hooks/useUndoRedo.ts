import { useCallback, useRef, useState } from "react";

interface HistoryEntry {
  type: "node" | "edge";
  action: "create" | "update" | "delete";
  before: unknown;
  after: unknown;
}

export function useUndoRedo() {
  const undoStack = useRef<HistoryEntry[]>([]);
  const redoStack = useRef<HistoryEntry[]>([]);
  const [, setTick] = useState(0);

  const push = useCallback((entry: HistoryEntry) => {
    undoStack.current.push(entry);
    redoStack.current = [];
    setTick((t) => t + 1);
  }, []);

  const canUndo = undoStack.current.length > 0;
  const canRedo = redoStack.current.length > 0;

  const popUndo = useCallback(() => {
    const entry = undoStack.current.pop();
    if (entry) {
      redoStack.current.push(entry);
      setTick((t) => t + 1);
    }
    return entry;
  }, []);

  const popRedo = useCallback(() => {
    const entry = redoStack.current.pop();
    if (entry) {
      undoStack.current.push(entry);
      setTick((t) => t + 1);
    }
    return entry;
  }, []);

  return { push, popUndo, popRedo, canUndo, canRedo };
}
