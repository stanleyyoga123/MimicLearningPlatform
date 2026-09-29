import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useModules } from '../../../../../src/features/modules/hooks/useModules';
import type { ModuleApi } from '../../../../../src/features/modules/services/ModuleApi';
import type { Module } from '../../../../../src/features/modules/schemas/module';

const runningModule: Module = {
  id: 'job-1', title: 'Webhook retries', status: 'running', stage: 'reference',
  created_at: '2026-09-29T00:00:00Z', updated_at: '2026-09-29T00:00:00Z',
  error: null, spec: null, peers: [], verification: null, repository_url: null, commit_sha: null,
};

afterEach(() => {
  vi.useRealTimers();
  window.location.hash = '';
});

describe('useModules', () => {
  it('waits for a progress request before scheduling the next poll', async () => {
    window.location.hash = 'module=job-1';
    vi.useFakeTimers();
    let finishFirst!: (value: Module) => void;
    const firstRequest = new Promise<Module>((resolve) => { finishFirst = resolve; });
    const get = vi.fn().mockReturnValueOnce(firstRequest).mockResolvedValueOnce({ ...runningModule, status: 'completed', stage: 'completed' });
    const api = { list: vi.fn().mockResolvedValue([]), get } as unknown as ModuleApi;

    const { unmount } = renderHook(() => useModules(api));
    expect(get).toHaveBeenCalledTimes(1);

    await act(async () => { await vi.advanceTimersByTimeAsync(4000); });
    expect(get).toHaveBeenCalledTimes(1);

    await act(async () => { finishFirst(runningModule); await firstRequest; });
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(get).toHaveBeenCalledTimes(2);
    unmount();
  });
});
