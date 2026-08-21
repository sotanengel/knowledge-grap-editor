/**
 * The application shell: three panes over a tabbed panel (§7.1).
 *
 * The default is exactly what §7.3-1 asks for — one screen, three panes, and
 * nothing else on show until the "詳細" switch is turned on.
 */
import { useState } from 'react';

import { GraphCanvas } from './components/canvas/GraphCanvas';
import { Inspector } from './components/inspector/Inspector';
import { Header } from './components/layout/Header';
import { BottomPanel, type PanelTab } from './components/panels/BottomPanel';
import { VocabularyPane } from './components/vocab/VocabularyPane';
import { GraphProvider, useGraph } from './state/graph';
import { SettingsProvider } from './state/settings';

export function App() {
  return (
    <SettingsProvider>
      <GraphProvider>
        <Workspace />
      </GraphProvider>
    </SettingsProvider>
  );
}

function Workspace() {
  const { error } = useGraph();
  const [tab, setTab] = useState<PanelTab>('sparql');
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-full flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <Header
        onOpenPanel={(next) => {
          setTab(next as PanelTab);
          setCollapsed(false);
        }}
      />

      {error && (
        <p
          role="alert"
          className="bg-red-100 px-4 py-2 text-sm text-red-900 dark:bg-red-900/40 dark:text-red-100"
        >
          サーバーに接続できません: {error}
        </p>
      )}

      <div className="flex min-h-0 flex-1">
        <VocabularyPane />
        <main className="min-w-0 flex-1">
          <GraphCanvas />
        </main>
        <Inspector />
      </div>

      <BottomPanel
        tab={tab}
        onTabChange={setTab}
        collapsed={collapsed}
        onToggle={() => setCollapsed((current) => !current)}
      />
    </div>
  );
}
