import type { ReactNode } from "react";
import EmptyInspector from "./EmptyInspector";

interface Props {
  children?: ReactNode;
}

export default function Inspector({ children }: Props) {
  return (
    <div className="inspector-panel" data-testid="inspector">
      {children ?? <EmptyInspector />}
    </div>
  );
}
