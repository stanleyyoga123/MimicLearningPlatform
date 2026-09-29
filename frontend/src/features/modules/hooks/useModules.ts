import { useCallback, useEffect, useState } from 'react';
import type { Module } from '../schemas/module';
import type { ModuleApi } from '../services/ModuleApi';

function selectedIdFromHash(): string | null {
  return new URLSearchParams(window.location.hash.slice(1)).get('module');
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}

export function useModules(api: ModuleApi) {
  const [items, setItems] = useState<Module[]>([]);
  const [selectedId, setSelectedId] = useState(selectedIdFromHash);
  const [selected, setSelected] = useState<Module | null>(null);
  const [loading, setLoading] = useState(Boolean(selectedId));
  const [listError, setListError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [refreshVersion, setRefreshVersion] = useState(0);

  const refreshList = useCallback(async () => {
    try {
      setItems(await api.list());
      setListError(null);
    } catch (error) {
      setListError(errorMessage(error));
    }
  }, [api]);

  useEffect(() => { void refreshList(); }, [refreshList]);
  useEffect(() => {
    const onHashChange = () => { setSelected(null); setSelectedId(selectedIdFromHash()); };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    if (!selectedId) { setSelected(null); setLoading(false); setDetailError(null); return; }
    let active = true;
    let timer: number | undefined;
    setLoading(true);
    setDetailError(null);
    const poll = async () => {
      try {
        const module = await api.get(selectedId);
        if (!active) return;
        setSelected(module);
        setLoading(false);
        setDetailError(null);
        setItems((previous) => [module, ...previous.filter((item) => item.id !== module.id)]);
        if (module.status === 'queued' || module.status === 'running') timer = window.setTimeout(poll, 2000);
      } catch (error) {
        if (!active) return;
        setLoading(false);
        setDetailError(errorMessage(error));
        timer = window.setTimeout(poll, 2000);
      }
    };
    void poll();
    return () => { active = false; window.clearTimeout(timer); };
  }, [api, selectedId, refreshVersion]);

  const select = (id: string | null) => {
    if (id === selectedId) return;
    window.location.hash = id ? `module=${encodeURIComponent(id)}` : '';
    setSelected(null);
    setSelectedId(id);
  };

  const create = async (input: { text?: string; file?: File }) => {
    setBusy(true);
    try {
      const module = await api.create(input);
      setItems((previous) => [module, ...previous.filter((item) => item.id !== module.id)]);
      select(module.id);
      return null;
    } catch (error) {
      return errorMessage(error);
    } finally {
      setBusy(false);
    }
  };

  const retry = async () => {
    if (!selectedId) return;
    setBusy(true);
    try {
      const module = await api.retry(selectedId);
      setSelected(module);
      setDetailError(null);
      setItems((previous) => [module, ...previous.filter((item) => item.id !== module.id)]);
      setRefreshVersion((version) => version + 1);
    } catch (error) {
      setDetailError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  return { items, selectedId, selected, loading, listError, detailError, busy, select, create, retry, refreshList };
}
