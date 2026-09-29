import { useCallback, useEffect, useRef, useState } from 'react';
import type { SessionStart } from '../schemas/session';
import { SessionApi, SessionApiError } from '../services/SessionApi';

export type ChatTurn = { role: 'learner' | 'assistant'; content: string };
export type PendingTurn = { agentId: string; question: string; reply: string };

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}

export function useWorkspaceSession(api: SessionApi) {
  const [moduleId, setModuleId] = useState<string | null>(null);
  const [session, setSession] = useState<SessionStart | null>(null);
  const [starting, setStarting] = useState(false);
  const [ended, setEnded] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [transcripts, setTranscripts] = useState<Record<string, ChatTurn[]>>({});
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busyAgentId, setBusyAgentId] = useState<string | null>(null);
  const [pendingTurn, setPendingTurn] = useState<PendingTurn | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sessionRef = useRef<SessionStart | null>(null);
  const messageAbortRef = useRef<AbortController | null>(null);
  const pendingStartRef = useRef(false);
  const attemptRef = useRef(0);
  const mountedRef = useRef(false);

  const markEnded = useCallback((sessionId: string) => {
    if (sessionRef.current?.id !== sessionId) return;
    sessionRef.current = null;
    messageAbortRef.current?.abort();
    messageAbortRef.current = null;
    setSession(null);
    setBusyAgentId(null);
    setPendingTurn(null);
    setEnded(true);
    setError(null);
    setTranscripts({});
    setDrafts({});
    setSelectedAgentId(null);
  }, []);

  const close = useCallback(async () => {
    attemptRef.current += 1;
    pendingStartRef.current = false;
    messageAbortRef.current?.abort();
    messageAbortRef.current = null;
    const current = sessionRef.current;
    sessionRef.current = null;
    setModuleId(null);
    setSession(null);
    setStarting(false);
    setEnded(false);
    setBusyAgentId(null);
    setPendingTurn(null);
    setError(null);
    setTranscripts({});
    setDrafts({});
    setSelectedAgentId(null);
    if (current) {
      try { await api.close(current.id); }
      catch { /* Session expiry also removes it; closing the workspace still succeeds. */ }
    }
  }, [api]);

  const start = useCallback(async (newModuleId: string) => {
    if (pendingStartRef.current || sessionRef.current) return;
    const attempt = ++attemptRef.current;
    pendingStartRef.current = true;
    setModuleId(newModuleId);
    setSession(null);
    setStarting(true);
    setEnded(false);
    setError(null);
    setTranscripts({});
    setDrafts({});
    setSelectedAgentId(null);
    try {
      const created = await api.start(newModuleId);
      if (!mountedRef.current || attempt !== attemptRef.current) {
        try { await api.close(created.id); }
        catch { /* The server will expire a session that cannot be closed. */ }
        return;
      }
      sessionRef.current = created;
      setSession(created);
      setSelectedAgentId(created.agents[0]?.id ?? null);
      setStarting(false);
    } catch (failure) {
      if (!mountedRef.current || attempt !== attemptRef.current) return;
      setStarting(false);
      setError(errorMessage(failure));
    } finally {
      if (attempt === attemptRef.current) pendingStartRef.current = false;
    }
  }, [api]);

  const send = useCallback(async (agentId: string) => {
    const current = sessionRef.current;
    const content = drafts[agentId]?.trim();
    if (!current || !content || busyAgentId || messageAbortRef.current || content.length > 4000) return;
    const controller = new AbortController();
    messageAbortRef.current = controller;
    setBusyAgentId(agentId);
    setError(null);
    setPendingTurn({ agentId, question: content, reply: '' });
    try {
      const reply = await api.send(current.id, agentId, content, controller.signal, (partial) => {
        if (sessionRef.current?.id === current.id && !controller.signal.aborted) {
          setPendingTurn({ agentId, question: content, reply: partial });
        }
      });
      if (sessionRef.current?.id !== current.id || controller.signal.aborted) return;
      setTranscripts((previous) => ({
        ...previous,
        [agentId]: [...(previous[agentId] ?? []), { role: 'learner', content }, { role: 'assistant', content: reply }],
      }));
      setDrafts((previous) => ({ ...previous, [agentId]: '' }));
    } catch (failure) {
      if (controller.signal.aborted || sessionRef.current?.id !== current.id) return;
      if (failure instanceof SessionApiError && failure.status === 404) markEnded(current.id);
      else setError(errorMessage(failure));
    } finally {
      if (messageAbortRef.current === controller) messageAbortRef.current = null;
      if (sessionRef.current?.id === current.id) {
        setBusyAgentId(null);
        setPendingTurn(null);
      }
    }
  }, [api, busyAgentId, drafts, markEnded]);

  useEffect(() => {
    mountedRef.current = true;
    const onPageHide = () => {
      attemptRef.current += 1;
      pendingStartRef.current = false;
      messageAbortRef.current?.abort();
      messageAbortRef.current = null;
      const current = sessionRef.current;
      sessionRef.current = null;
      if (current) api.closeOnUnload(current.id);
      setSession(null);
      setStarting(false);
      setEnded(true);
      setBusyAgentId(null);
      setPendingTurn(null);
      setTranscripts({});
      setDrafts({});
      setSelectedAgentId(null);
    };
    window.addEventListener('pagehide', onPageHide);
    return () => {
      mountedRef.current = false;
      attemptRef.current += 1;
      pendingStartRef.current = false;
      messageAbortRef.current?.abort();
      const current = sessionRef.current;
      sessionRef.current = null;
      if (current) api.closeOnUnload(current.id);
      window.removeEventListener('pagehide', onPageHide);
    };
  }, [api]);

  useEffect(() => {
    if (!session) return;
    const timer = window.setInterval(() => {
      void api.heartbeat(session.id).catch((failure: unknown) => {
        if (failure instanceof SessionApiError && failure.status === 404) markEnded(session.id);
      });
    }, 20_000);
    return () => window.clearInterval(timer);
  }, [api, markEnded, session]);

  return {
    moduleId, session, starting, ended, selectedAgentId, transcripts, drafts, busyAgentId, pendingTurn, error,
    start, close, send, selectAgent: setSelectedAgentId,
    setDraft: (agentId: string, content: string) => setDrafts((previous) => ({ ...previous, [agentId]: content })),
  };
}
