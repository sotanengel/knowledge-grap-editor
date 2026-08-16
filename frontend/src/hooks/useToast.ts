import { createContext, useContext } from "react";
import type { ToastMessage, ToastType } from "./ToastProvider";

interface ToastContextValue {
  toasts: ToastMessage[];
  showToast: (type: ToastType, text: string) => void;
  dismissToast: (id: number) => void;
}

export const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
