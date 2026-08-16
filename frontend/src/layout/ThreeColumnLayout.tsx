import type { ReactNode } from "react";

interface Props {
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
  leftCollapsed?: boolean;
  rightDrawerOpen?: boolean;
}

export default function ThreeColumnLayout({
  left,
  center,
  right,
  leftCollapsed = false,
  rightDrawerOpen = false,
}: Props) {
  return (
    <div className="three-column-layout">
      <aside
        className={`pane-left${leftCollapsed ? " collapsed" : ""}`}
        data-testid="pane-left"
      >
        {left}
      </aside>
      <main className="pane-center" data-testid="pane-center">
        {center}
      </main>
      <aside
        className={`pane-right${rightDrawerOpen ? " drawer-open" : ""}`}
        data-testid="pane-right"
      >
        {right}
      </aside>
    </div>
  );
}
