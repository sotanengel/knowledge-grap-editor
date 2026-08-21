/**
 * The application shell.
 *
 * PR1 only establishes the frame; the three-pane editor described in §7.1
 * arrives with the UI PR.
 */
export function App() {
  return (
    <div className="flex h-full flex-col bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="flex items-center gap-3 border-b border-slate-200 px-4 py-3 dark:border-slate-800">
        <h1 className="text-lg font-semibold">OntoForge</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          オントロジー／ナレッジグラフ オーサリングツール
        </p>
      </header>
      <main className="flex flex-1 items-center justify-center">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          エディタはこれから実装されます。
        </p>
      </main>
    </div>
  );
}
