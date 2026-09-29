import { useCallback, useEffect, useRef, useState } from 'react';
import type { Submission } from '../schemas/submission';
import type { SubmissionApi } from '../services/SubmissionApi';

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Could not load submissions. Please try again.';
}

function newestFirst(records: Submission[]): Submission[] {
  return [...records].sort((left, right) => right.created_at.localeCompare(left.created_at));
}

function mergeRecords(moduleId: string, incoming: Submission[], current: Submission[]): Submission[] {
  const byId = new Map(incoming.map((record) => [record.id, record]));
  for (const record of current) {
    if (record.module_id !== moduleId) continue;
    const received = byId.get(record.id);
    if (!received || record.updated_at >= received.updated_at) byId.set(record.id, record);
  }
  return newestFirst([...byId.values()]);
}

export function useSubmissions(api: SubmissionApi, moduleId: string | null) {
  const [records, setRecords] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadedGeneration, setLoadedGeneration] = useState<number | null>(null);
  const [busyGeneration, setBusyGeneration] = useState<number | null>(null);
  const [error, setError] = useState<{ generation: number; message: string } | null>(null);
  const [reload, setReload] = useState(0);
  const contextRef = useRef({ moduleId, generation: 0 });
  const mountedRef = useRef(false);
  const mutationRef = useRef<{ token: symbol; generation: number } | null>(null);
  if (contextRef.current.moduleId !== moduleId) {
    contextRef.current = { moduleId, generation: contextRef.current.generation + 1 };
  }
  const generation = contextRef.current.generation;

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  useEffect(() => {
    if (!moduleId) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    setError(null);
    setLoading(true);
    const poll = async () => {
      try {
        const items = await api.list(moduleId, controller.signal);
        if (controller.signal.aborted || contextRef.current.generation !== generation) return;
        setRecords((current) => mergeRecords(moduleId, items, current));
        setLoadedGeneration(generation);
        setError(null);
      } catch (failure) {
        if (!controller.signal.aborted && contextRef.current.generation === generation) {
          setError({ generation, message: errorMessage(failure) });
        }
      } finally {
        if (!controller.signal.aborted && contextRef.current.generation === generation) {
          setLoading(false);
          // New reviews can arrive through GitHub even when no local job is active.
          timer = setTimeout(() => void poll(), 2000);
        }
      }
    };
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [api, moduleId, reload, generation]);

  const update = (record: Submission) => {
    setRecords((current) => mergeRecords(record.module_id, [record], current));
  };

  const submit = useCallback(async (prUrl: string): Promise<boolean> => {
    if (!moduleId || loadedGeneration !== generation || loading || mutationRef.current?.generation === generation) return false;
    const request = Symbol('submit');
    mutationRef.current = { token: request, generation };
    setBusyGeneration(generation);
    setError(null);
    try {
      const record = await api.create(moduleId, prUrl.trim());
      if (mountedRef.current && contextRef.current.generation === generation) update(record);
      return mountedRef.current && contextRef.current.generation === generation;
    } catch (failure) {
      if (mountedRef.current && contextRef.current.generation === generation) {
        setError({ generation, message: errorMessage(failure) });
      }
      return false;
    } finally {
      if (mutationRef.current?.token === request) {
        mutationRef.current = null;
        if (mountedRef.current && contextRef.current.generation === generation) setBusyGeneration(null);
      }
    }
  }, [api, moduleId, generation, loadedGeneration, loading]);

  const retry = useCallback(async (submissionId: string): Promise<void> => {
    if (!moduleId || loadedGeneration !== generation || loading || mutationRef.current?.generation === generation) return;
    const request = Symbol('retry');
    mutationRef.current = { token: request, generation };
    setBusyGeneration(generation);
    setError(null);
    try {
      const record = await api.retry(submissionId);
      if (mountedRef.current && contextRef.current.generation === generation) update(record);
    } catch (failure) {
      if (mountedRef.current && contextRef.current.generation === generation) {
        setError({ generation, message: errorMessage(failure) });
      }
    } finally {
      if (mutationRef.current?.token === request) {
        mutationRef.current = null;
        if (mountedRef.current && contextRef.current.generation === generation) setBusyGeneration(null);
      }
    }
  }, [api, moduleId, generation, loadedGeneration, loading]);

  return {
    records: loadedGeneration === generation ? records.filter((record) => record.module_id === moduleId) : [],
    loading: moduleId !== null && loading,
    ready: loadedGeneration === generation && !loading,
    busy: busyGeneration === generation,
    error: error?.generation === generation ? error.message : null,
    submit,
    retry,
    refresh: () => setReload((value) => value + 1),
  };
}
