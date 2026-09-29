import { describe, expect, it, vi } from 'vitest';
import { ModuleApi } from '../../../../../src/features/modules/services/ModuleApi';

const moduleRecord = {
  id: 'abc', title: 'Webhook retries', status: 'queued', stage: 'queued',
  created_at: '2026-09-29T00:00:00Z', updated_at: '2026-09-29T00:00:00Z',
  error: null, spec: null, peers: [], verification: null, repository_url: null, commit_sha: null,
};

describe('ModuleApi', () => {
  it('submits the document as multipart form data', async () => {
    const request = vi.fn(async (url: string, options?: RequestInit) => {
      expect(url).toBe('/api/modules');
      expect(options?.method).toBe('POST');
      return new Response(JSON.stringify(moduleRecord), { status: 201 });
    });
    const api = new ModuleApi('/api', request as typeof fetch);
    const file = new File(['incident'], 'incident.md', { type: 'text/markdown' });

    const result = await api.create({ file });

    expect(result.id).toBe('abc');
    expect(request).toHaveBeenCalledWith('/api/modules', expect.objectContaining({ method: 'POST' }));
    const body = request.mock.calls[0]?.[1]?.body as FormData;
    expect(body.get('file')).toBe(file);
  });

  it('rejects a malformed module response at the API boundary', async () => {
    const api = new ModuleApi('/api', vi.fn(async () => new Response(JSON.stringify({ id: 'abc' }))) as typeof fetch);
    await expect(api.get('abc')).rejects.toThrow();
  });

  it('shows the backend failure detail', async () => {
    const api = new ModuleApi('/api', vi.fn(async () => new Response(JSON.stringify({ detail: 'PDF has no extractable text' }), { status: 422 })) as typeof fetch);
    await expect(api.create({ text: 'source' })).rejects.toThrow('PDF has no extractable text');
  });

  it('calls an injected fetch without binding the API client as its receiver', async () => {
    const request = vi.fn(function (this: unknown) {
      if (this !== undefined) throw new TypeError('Illegal invocation');
      return Promise.resolve(new Response(JSON.stringify(moduleRecord)));
    });
    const api = new ModuleApi('/api', request as typeof fetch);

    await expect(api.get('abc')).resolves.toMatchObject({ id: 'abc' });
    expect(request).toHaveBeenCalledTimes(1);
  });
});
