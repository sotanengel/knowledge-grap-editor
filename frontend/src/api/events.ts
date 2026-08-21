/** The change feed, so an open tab notices edits made elsewhere (§8). */
import type { ChangeEvent } from './types';

export type ChangeListener = (event: ChangeEvent) => void;

/**
 * Subscribe to `GET /events`. Returns an unsubscribe function.
 *
 * `EventSource` reconnects on its own, so nothing here needs to retry.
 */
export function subscribeToChanges(listener: ChangeListener, url = '/api/v1/events'): () => void {
  if (typeof EventSource === 'undefined') return () => {};

  const source = new EventSource(url);
  const handle = (event: MessageEvent<string>) => {
    try {
      listener({
        ...(JSON.parse(event.data) as ChangeEvent),
        type: event.type as ChangeEvent['type'],
      });
    } catch {
      // A frame we cannot read is not worth breaking the stream over.
    }
  };

  for (const name of ['ready', 'change', 'undo', 'redo']) {
    source.addEventListener(name, handle as EventListener);
  }
  return () => source.close();
}
