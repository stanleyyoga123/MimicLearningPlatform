import { useCallback, useEffect, useState } from 'react';
import type { Module } from '../schemas/module';
import type { ModuleApi } from '../services/ModuleApi';

export type AvailableModule = Module & {
  spec: NonNullable<Module['spec']>;
  repository_url: string;
};

function isAvailable(module: Module): module is AvailableModule {
  return module.status === 'completed' && module.spec !== null && module.repository_url !== null;
}

function selectedIdFromHash(): string | null {
  return new URLSearchParams(window.location.hash.slice(1)).get('module');
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Could not load available modules.';
}

export function useAvailableModules(api: ModuleApi) {
  const [items, setItems] = useState<AvailableModule[]>([]);
  const [selectedId, setSelectedId] = useState(selectedIdFromHash);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setItems((await api.list()).filter(isAvailable));
      setError(null);
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    const onHashChange = () => setSelectedId(selectedIdFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const select = (id: string | null) => {
    window.location.hash = id ? `module=${encodeURIComponent(id)}` : '';
    setSelectedId(id);
  };

  return {
    items,
    selectedId,
    selected: items.find((item) => item.id === selectedId) ?? null,
    loading,
    error,
    refresh,
    select,
  };
}
