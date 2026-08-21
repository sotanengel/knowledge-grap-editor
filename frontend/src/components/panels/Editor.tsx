/** A CodeMirror 6 editor with Turtle or SPARQL highlighting (§5.3). */
import { useEffect, useRef } from 'react';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import { StreamLanguage, bracketMatching, indentOnInput } from '@codemirror/language';
import { sparql } from '@codemirror/legacy-modes/mode/sparql';
import { turtle } from '@codemirror/legacy-modes/mode/turtle';
import { EditorState, type Extension } from '@codemirror/state';
import { EditorView, highlightActiveLine, keymap, lineNumbers } from '@codemirror/view';

const LANGUAGES: Record<'turtle' | 'sparql', Extension> = {
  turtle: StreamLanguage.define(turtle),
  sparql: StreamLanguage.define(sparql),
};

interface Props {
  value: string;
  language: 'turtle' | 'sparql';
  readOnly?: boolean;
  onChange?: (value: string) => void;
  onSubmit?: () => void;
  className?: string;
  ariaLabel: string;
}

export function Editor({
  value,
  language,
  readOnly = false,
  onChange,
  onSubmit,
  className = '',
  ariaLabel,
}: Props) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const latestSubmit = useRef(onSubmit);
  latestSubmit.current = onSubmit;

  useEffect(() => {
    if (!host.current) return undefined;

    const state = EditorState.create({
      doc: value,
      extensions: [
        lineNumbers(),
        history(),
        bracketMatching(),
        indentOnInput(),
        highlightActiveLine(),
        LANGUAGES[language],
        keymap.of([
          {
            key: 'Mod-Enter',
            run: () => {
              latestSubmit.current?.();
              return true;
            },
          },
          ...defaultKeymap,
          ...historyKeymap,
        ]),
        EditorView.editable.of(!readOnly),
        EditorState.readOnly.of(readOnly),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) onChange?.(update.state.doc.toString());
        }),
        EditorView.theme({
          '&': { fontSize: '12px', height: '100%' },
          '.cm-scroller': { overflow: 'auto' },
        }),
      ],
    });

    const instance = new EditorView({ state, parent: host.current });
    instance.contentDOM.setAttribute('aria-label', ariaLabel);
    view.current = instance;
    return () => {
      instance.destroy();
      view.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language, readOnly]);

  // Replace the document only when the value changed elsewhere, so typing is
  // never interrupted by a refresh.
  useEffect(() => {
    const instance = view.current;
    if (!instance) return;
    const current = instance.state.doc.toString();
    if (current === value) return;
    instance.dispatch({ changes: { from: 0, to: current.length, insert: value } });
  }, [value]);

  return <div ref={host} className={`h-full overflow-hidden ${className}`} data-testid="editor" />;
}
