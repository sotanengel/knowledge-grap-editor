import { useCallback, useState, type ReactNode } from "react";
import { ToastContext } from "../hooks/useToast";

export type ToastType = "success" | "error";

export interface ToastMessage {
  id: number;
  type: ToastType;
  text: string;
}

let toastId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback((type: ToastType, text: string) => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, type, text }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, showToast, dismissToast }}>
      {children}
      <div className="toast-container" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.type}`} role="status">
            {t.type === "success" ? "✓ " : "⚠ "}
            {t.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
