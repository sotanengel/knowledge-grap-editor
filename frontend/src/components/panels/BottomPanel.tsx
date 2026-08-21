/** The bottom tabs: SPARQL, Turtle, validation results and history (§7.1). */
import { useState } from 'react';

import { useGraph } from '../../state/graph';
import { CsvImportDialog } from './CsvImportDialog';
import { HistoryPanel } from './HistoryPanel';
import { SemanticPanel } from './SemanticPanel';
import { SparqlConsole } from './SparqlConsole';
import { TurtleView } from './TurtleView';
import { ValidationPanel } from './ValidationPanel';

export type PanelTab = 'sparql' | 'turtle' | 'validation' | 'history' | 'semantic';

const TABS: { id: PanelTab; label: string }[] = [
  { id: 'sparql', label: 'SPARQL' },
  { id: 'turtle', label: 'Turtle ビュー' },
  { id: 'validation', label: '検証結果' },
  { id: 'history', label: '履歴' },
  { id: 'semantic', label: '類似検索' },
];

interface Props {
  tab: PanelTab;
  onTabChange: (tab: PanelTab) => void;
  collapsed: boolean;
  onToggle: () => void;
}

export function BottomPanel({ tab, onTabChange, collapsed, onToggle }: Props) {
  const { validation } = useGraph();
  const [importing, setImporting] = useState(false);

  return (
    <section
      className="flex flex-col border-t border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
      style={{ height: collapsed ? 'auto' : '38%' }}
    >
      <div
        role="tablist"
        aria-label="下部パネル"
        className="flex items-center gap-1 border-b border-slate-200 px-2 dark:border-slate-800"
      >
        {TABS.map((entry) => (
          <button
            key={entry.id}
            role="tab"
            aria-selected={!collapsed && tab === entry.id}
            onClick={() => {
              onTabChange(entry.id);
              if (collapsed) onToggle();
            }}
            className={`px-3 py-1.5 text-xs ${
              !collapsed && tab === entry.id
                ? 'border-b-2 border-blue-600 font-medium text-blue-700 dark:text-blue-300'
                : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            {entry.label}
            {entry.id === 'validation' && validation && !validation.conforms && (
              <span className="ml-1 rounded-full bg-red-600 px-1.5 text-[10px] text-white">
                {validation.findings.length}
              </span>
            )}
          </button>
        ))}

        <button
          type="button"
          onClick={() => setImporting(true)}
          className="ml-auto px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400"
        >
          表データを取り込む
        </button>
        <button
          type="button"
          onClick={onToggle}
          aria-label={collapsed ? 'パネルを開く' : 'パネルを閉じる'}
          className="px-2 py-1.5 text-xs text-slate-500"
        >
          {collapsed ? '▲' : '▼'}
        </button>
      </div>

      {!collapsed && (
        <div role="tabpanel" className="min-h-0 flex-1 overflow-hidden">
          {tab === 'sparql' && <SparqlConsole />}
          {tab === 'turtle' && <TurtleView />}
          {tab === 'validation' && <ValidationPanel />}
          {tab === 'history' && <HistoryPanel />}
          {tab === 'semantic' && <SemanticPanel />}
        </div>
      )}

      {importing && <CsvImportDialog onClose={() => setImporting(false)} />}
    </section>
  );
}
