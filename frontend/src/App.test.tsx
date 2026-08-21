import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { App } from './App';

// The canvas needs a real 2d context, which jsdom has not got. Its own mapping
// is covered by the tests around `buildElements`; here we only care that the
// shell puts the three panes and the tabs in place.
vi.mock('./components/canvas/GraphCanvas', () => ({
  GraphCanvas: () => <div data-testid="graph-canvas" />,
}));

// jsdom has no ResizeObserver, and the canvas installs one.
class NoopResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', NoopResizeObserver);

const HEALTH = {
  status: 'ok',
  version: '0.1.0',
  quads: 0,
  base_iri: 'https://example.org/kg/',
  reasoner: 'rdfs',
  auth_required: false,
};

const ONTOLOGY = {
  classes: [
    {
      iri: 'https://example.org/kg/ont#Person',
      label: '人物',
      comment: null,
      types: [],
      parents: [],
      domain: [],
      range: [],
      instanceCount: 2,
      children: [],
    },
  ],
  properties: [],
};

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal('EventSource', undefined);
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/health')) return Promise.resolve(jsonResponse(HEALTH));
      if (url.includes('/ontology')) return Promise.resolve(jsonResponse(ONTOLOGY));
      if (url.includes('/entities'))
        return Promise.resolve(
          jsonResponse({ '@context': {}, '@graph': [], limit: 200, offset: 0 }),
        );
      if (url.includes('/vocabularies'))
        return Promise.resolve(
          jsonResponse({
            available: [
              {
                name: 'skos',
                title: 'SKOS',
                prefix: 'skos',
                namespace: 'http://www.w3.org/2004/02/skos/core#',
                licence: 'W3C',
              },
            ],
            loaded: [],
            defaults: ['skos'],
          }),
        );
      if (url.includes('/sparql'))
        return Promise.resolve(jsonResponse({ head: { vars: [] }, results: { bindings: [] } }));
      if (url.includes('/history'))
        return Promise.resolve(jsonResponse({ entries: [], can_undo: false, can_redo: false }));
      return Promise.resolve(jsonResponse({}));
    }),
  );
});

describe('the workspace shell', () => {
  it('lays out three panes over a tabbed panel (§7.1)', async () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: 'OntoForge' })).toBeInTheDocument();
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument();
    expect(screen.getByRole('tablist', { name: '下部パネル' })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('人物')).toBeInTheDocument());
  });

  it('speaks plainly by default and switches to jargon on request (§7.3-2)', async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(screen.getByPlaceholderText('項目を名前で検索')).toBeInTheDocument();
    await user.click(screen.getByLabelText('専門用語表記'));
    expect(screen.getByPlaceholderText('インスタンスを名前で検索')).toBeInTheDocument();
  });

  it('keeps the advanced detail behind a toggle (§7.3-1)', async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByText('人物')).toBeInTheDocument());

    expect(screen.queryByText('ont:Person')).not.toBeInTheDocument();
    await user.click(screen.getByLabelText('詳細'));
    await waitFor(() => expect(screen.getByText('Person')).toBeInTheDocument());
  });

  it('offers the panel tabs the specification names', () => {
    render(<App />);
    for (const label of ['SPARQL', 'Turtle ビュー', '検証結果', '履歴']) {
      expect(screen.getByRole('tab', { name: new RegExp(label) })).toBeInTheDocument();
    }
  });

  it('shows the empty inspector until something is selected', () => {
    render(<App />);
    expect(screen.getByText(/選ぶと、ここに詳細が出ます/)).toBeInTheDocument();
  });

  it('lists the bundled vocabularies without going to the network', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('button', { name: /外部語彙/ }));
    await waitFor(() => expect(screen.getByText('SKOS')).toBeInTheDocument());
    expect(screen.getByText(/外部への通信は行いません/)).toBeInTheDocument();
  });
});

describe('reusing a vocabulary term', () => {
  it('lets a class be dragged out of the left pane (§7.2)', async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText('人物')).toBeInTheDocument());
    const term = screen.getByRole('button', { name: /人物/ });
    expect(term).toHaveAttribute('draggable', 'true');
  });
});
