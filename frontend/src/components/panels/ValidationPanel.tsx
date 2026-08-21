/** Validation results (§10.2), each with the repair the user can carry out. */
import { useGraph } from '../../state/graph';
import { shortIri } from '../../lib/iri';

export function ValidationPanel() {
  const { validation, select } = useGraph();

  if (!validation) {
    return (
      <p className="p-4 text-sm text-slate-500">
        ヘッダの「検証」を押すと、決めた制約に合っているかを確認します。
      </p>
    );
  }

  if (validation.conforms) {
    return (
      <p className="p-4 text-sm text-emerald-700 dark:text-emerald-300">
        {validation.shapes} 件の制約すべてに適合しています。
      </p>
    );
  }

  return (
    <div className="h-full overflow-auto p-2">
      <p className="mb-2 text-sm">
        {validation.findings.length} 件の違反（{validation.violated.length} 項目）
      </p>
      <ul className="space-y-2">
        {validation.findings.map((finding, index) => (
          <li
            key={`${finding.focusNode}-${finding.constraint}-${index}`}
            className="rounded-md border border-red-200 bg-red-50 p-2 text-xs dark:border-red-900 dark:bg-red-900/20"
          >
            <button
              type="button"
              onClick={() => select(finding.focusNode)}
              className="font-medium text-red-800 hover:underline dark:text-red-200"
            >
              {finding.focusLabel || shortIri(finding.focusNode)}
            </button>
            <p className="mt-1 text-red-900 dark:text-red-100">{finding.suggestion}</p>
            {finding.message && (
              <p className="mt-1 text-[10px] text-red-700 dark:text-red-300">{finding.message}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
