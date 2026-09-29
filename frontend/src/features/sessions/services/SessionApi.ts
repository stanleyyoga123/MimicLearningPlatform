import { sessionStartSchema, sessionStreamEventSchema, type SessionStart } from '../schemas/session';

export class SessionApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = 'SessionApiError';
  }
}

export class SessionApi {
  constructor(private readonly baseUrl: string, private readonly request: typeof fetch) {}

  async start(moduleId: string): Promise<SessionStart> {
    return sessionStartSchema.parse(await this.read(`/modules/${encodeURIComponent(moduleId)}/sessions`, { method: 'POST' }));
  }

  async send(
    sessionId: string,
    agentId: string,
    content: string,
    signal: AbortSignal,
    onDelta: (content: string) => void,
  ): Promise<string> {
    let response: Response;
    try {
      const request = this.request;
      response = await request(`${this.baseUrl}/sessions/${encodeURIComponent(sessionId)}/messages`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId, content }), signal,
      });
    } catch (error) {
      if (signal.aborted) throw error;
      throw new SessionApiError('Could not reach the local API. Please try again.', 0);
    }

    if (!response.ok) {
      const payload: unknown = await response.json().catch(() => null);
      const detail = payload && typeof payload === 'object' && 'detail' in payload ? payload.detail : null;
      throw new SessionApiError(typeof detail === 'string' ? detail : `Request failed (${response.status}).`, response.status);
    }
    if (!response.body) throw new SessionApiError('The assistant reply could not be streamed. Please try again.', 0);

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8', { fatal: true });
    let buffer = '';
    let reply = '';
    let completed = false;

    const consumeLine = (line: string) => {
      if (!line.trim()) return;
      let parsed: unknown;
      try { parsed = JSON.parse(line); }
      catch { throw new SessionApiError('The assistant sent an invalid response. Please try again.', 0); }
      const event = sessionStreamEventSchema.safeParse(parsed);
      if (!event.success) throw new SessionApiError('The assistant sent an invalid response. Please try again.', 0);
      if (event.data.agent_id !== agentId || completed) {
        throw new SessionApiError('The assistant sent an unexpected response. Please try again.', 0);
      }
      if (event.data.type === 'error') throw new SessionApiError(event.data.detail, event.data.status);
      if (event.data.type === 'done') { completed = true; return; }
      reply += event.data.content;
      onDelta(reply);
    };

    try {
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        let newline = buffer.indexOf('\n');
        while (newline !== -1) {
          consumeLine(buffer.slice(0, newline).replace(/\r$/, ''));
          buffer = buffer.slice(newline + 1);
          newline = buffer.indexOf('\n');
        }
      }
      buffer += decoder.decode();
      if (buffer.trim()) throw new SessionApiError('The assistant reply ended unexpectedly. Please try again.', 0);
      if (!completed) throw new SessionApiError('The assistant reply ended unexpectedly. Please try again.', 0);
      return reply;
    } catch (error) {
      if (signal.aborted || error instanceof SessionApiError) throw error;
      throw new SessionApiError('The assistant reply was interrupted. Please try again.', 0);
    } finally {
      await reader.cancel().catch(() => {});
      reader.releaseLock();
    }
  }

  async heartbeat(sessionId: string): Promise<void> {
    await this.read(`/sessions/${encodeURIComponent(sessionId)}/heartbeat`, { method: 'POST' });
  }

  async close(sessionId: string): Promise<void> {
    await this.read(`/sessions/${encodeURIComponent(sessionId)}/close`, { method: 'POST' });
  }

  closeOnUnload(sessionId: string): void {
    const url = `${this.baseUrl}/sessions/${encodeURIComponent(sessionId)}/close`;
    if (typeof navigator.sendBeacon === 'function' && navigator.sendBeacon(url)) return;
    const request = this.request;
    void request(url, { method: 'POST', keepalive: true }).catch(() => {});
  }

  private async read(path: string, options: RequestInit): Promise<unknown> {
    let response: Response;
    try {
      const request = this.request;
      response = await request(`${this.baseUrl}${path}`, options);
    } catch (error) {
      if (options.signal?.aborted) throw error;
      throw new SessionApiError('Could not reach the local API. Please try again.', 0);
    }
    if (response.status === 204) return null;
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = payload && typeof payload === 'object' && 'detail' in payload ? payload.detail : null;
      throw new SessionApiError(typeof detail === 'string' ? detail : `Request failed (${response.status}).`, response.status);
    }
    return payload;
  }
}
