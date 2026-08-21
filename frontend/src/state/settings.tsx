/** Interface preferences: everyday words by default, jargon on request (§7.3). */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { api } from '../api/client';
import type { Health } from '../api/types';
import { termsFor, type TermSet, type Terminology } from '../i18n/terms';

const STORAGE_KEY = 'ontoforge.settings';
const FALLBACK: Stored = { terminology: 'plain', showDetails: false };

interface Stored {
  terminology: Terminology;
  showDetails: boolean;
}

interface SettingsValue extends Stored {
  terms: TermSet;
  health: Health | null;
  baseIri: string;
  setTerminology: (mode: Terminology) => void;
  setShowDetails: (show: boolean) => void;
}

const SettingsContext = createContext<SettingsValue | null>(null);

function read(): Stored {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...FALLBACK, ...(JSON.parse(raw) as Partial<Stored>) };
  } catch {
    // A corrupt preference is not worth failing startup over.
  }
  return FALLBACK;
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [stored, setStored] = useState<Stored>(read);
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  }, [stored]);

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const setTerminology = useCallback(
    (terminology: Terminology) => setStored((current) => ({ ...current, terminology })),
    [],
  );
  const setShowDetails = useCallback(
    (showDetails: boolean) => setStored((current) => ({ ...current, showDetails })),
    [],
  );

  const value = useMemo<SettingsValue>(
    () => ({
      ...stored,
      terms: termsFor(stored.terminology),
      health,
      baseIri: health?.base_iri ?? 'https://example.org/kg/',
      setTerminology,
      setShowDetails,
    }),
    [stored, health, setTerminology, setShowDetails],
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): SettingsValue {
  const value = useContext(SettingsContext);
  if (!value) throw new Error('useSettings must be used inside a SettingsProvider');
  return value;
}
