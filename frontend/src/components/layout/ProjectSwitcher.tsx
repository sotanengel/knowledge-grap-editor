/**
 * Switching between graph spaces (FR-14).
 *
 * Switching swaps everything: the graph, the history and the undo stack. That
 * is said out loud rather than left to be discovered.
 */
import { useCallback, useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { ProjectList } from '../../api/types';
import { useGraph } from '../../state/graph';
import { Dialog } from './Dialog';
import { ErrorNote } from './ErrorNote';

export function ProjectSwitcher() {
  const { refresh, select } = useGraph();
  const [list, setList] = useState<ProjectList | null>(null);
  const [managing, setManaging] = useState(false);
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .projects()
      .then(setList)
      .catch(() => setList(null));
  }, []);

  useEffect(load, [load]);

  const act = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      load();
      select(null);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  // A single project is the normal case; the switcher only appears once there
  // is something to switch between, or when the user opens the manager.
  if (!list) return null;

  return (
    <>
      <label className="flex items-center gap-1 text-sm">
        <span className="sr-only">プロジェクト</span>
        <select
          value={list.current}
          disabled={busy}
          onChange={(event) => void act(() => api.switchProject(event.target.value))}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
        >
          {list.projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        onClick={() => setManaging(true)}
        aria-label="プロジェクトを管理"
        title="プロジェクトを管理"
        className="rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-600"
      >
        ⚙
      </button>

      {managing && (
        <Dialog title="プロジェクト" onClose={() => setManaging(false)}>
          <div className="space-y-4">
            <p className="text-xs text-slate-500">
              プロジェクトを切り替えると、グラフ・履歴・元に戻す操作がまとめて入れ替わります。
              互いに混ざることはありません。
            </p>

            <ul className="space-y-1">
              {list.projects.map((project) => (
                <li key={project.id} className="flex items-center gap-2 text-sm">
                  <span className="flex-1">
                    {project.name}
                    {project.id === list.current && (
                      <span className="ml-1 text-xs text-blue-600 dark:text-blue-400">
                        （表示中）
                      </span>
                    )}
                  </span>
                  {project.id !== 'default' && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => {
                        if (!window.confirm(`「${project.name}」を中身ごと削除しますか？`)) return;
                        void act(() => api.deleteProject(project.id));
                      }}
                      className="text-xs text-red-600 hover:underline"
                    >
                      削除
                    </button>
                  )}
                </li>
              ))}
            </ul>

            <form
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (!name.trim()) return;
                void act(async () => {
                  const created = await api.createProject(name.trim());
                  setName('');
                  await api.switchProject(created.id);
                });
              }}
            >
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="新しいプロジェクト名"
                className="flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
              />
              <button
                type="submit"
                disabled={busy || !name.trim()}
                className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
              >
                作る
              </button>
            </form>

            <ErrorNote message={error} />
          </div>
        </Dialog>
      )}
    </>
  );
}
