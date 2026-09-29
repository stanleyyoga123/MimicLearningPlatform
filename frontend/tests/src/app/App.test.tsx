import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { App } from '../../../src/app/App';
import { ModuleApi } from '../../../src/features/modules/services/ModuleApi';
import { SessionApi } from '../../../src/features/sessions/services/SessionApi';
import { SubmissionApi } from '../../../src/features/submissions/services/SubmissionApi';
import { learnerModule } from '../../fixtures/modules/learnerModule';

afterEach(() => window.history.replaceState(null, '', '/'));
const submissionApi = new SubmissionApi('', vi.fn<typeof fetch>().mockResolvedValue(new Response('[]')));

function apiWithModules(items = [learnerModule()]) {
  const request = vi.fn<typeof fetch>().mockImplementation(async (input) => {
    const path = String(input);
    const data = path === '/modules' ? items : items.find((item) => path === `/modules/${item.id}`);
    return new Response(JSON.stringify(data ?? { detail: 'Module not found' }), { status: data ? 200 : 404 });
  });
  return { api: new ModuleApi('', request), sessionApi: new SessionApi('', request), request };
}

it('shows only published completed modules in the junior catalog', async () => {
  window.history.replaceState(null, '', '/junior');
  const { api, sessionApi } = apiWithModules([
    learnerModule(),
    learnerModule({ id: 'running', title: 'Still generating', status: 'running', stage: 'reference' }),
    learnerModule({ id: 'failed', title: 'Publication failed', status: 'failed', stage: 'publishing' }),
    learnerModule({ id: 'unpublished', title: 'No repository', repository_url: null }),
  ]);

  render(<App api={api} sessionApi={sessionApi} submissionApi={submissionApi} />);

  expect(await screen.findByText('Webhook idempotency')).toBeInTheDocument();
  expect(screen.queryByText('Still generating')).not.toBeInTheDocument();
  expect(screen.queryByText('Publication failed')).not.toBeInTheDocument();
  expect(screen.queryByText('No repository')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /generate module/i })).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: /senior/i })).toHaveAttribute('href', '/senior');
});

it('lets juniors open an available task from the catalog', async () => {
  window.history.replaceState(null, '', '/junior');
  const { api, sessionApi } = apiWithModules();

  render(<App api={api} sessionApi={sessionApi} submissionApi={submissionApi} />);

  await screen.findByText('Webhook idempotency');
  fireEvent.click(screen.getByRole('button', { name: /open webhook idempotency/i }));
  expect(await screen.findByText('Make webhook processing idempotent.')).toBeInTheDocument();
  expect(window.location.hash).toBe('#module=ready-1');
});

it('shows an empty junior task board without a submission form', async () => {
  window.history.replaceState(null, '', '/junior');
  const { api, sessionApi } = apiWithModules([]);

  render(<App api={api} sessionApi={sessionApi} submissionApi={submissionApi} />);

  expect(await screen.findByText('No tasks available yet')).toBeInTheDocument();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
});

it('loads a junior task directly from its URL without author diagnostics or controls', async () => {
  window.history.replaceState(null, '', '/junior#module=ready-1');
  const { api, sessionApi, request } = apiWithModules();

  render(<App api={api} sessionApi={sessionApi} submissionApi={submissionApi} />);

  expect(await screen.findByText('Make webhook processing idempotent.')).toBeInTheDocument();
  expect(screen.getByText('A repeated event creates only one order.')).toBeInTheDocument();
  expect(screen.getByText('Maya')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /open starter repository/i })).toHaveAttribute('href', 'https://github.com/example/webhook-exercise');
  expect(screen.queryByText('Author verification diagnostics')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /retry generation/i })).not.toBeInTheDocument();
  expect(request.mock.calls.every(([, options]) => !options?.method || options.method === 'GET')).toBe(true);
});

it('does not expose an unfinished module through a direct junior URL', async () => {
  window.history.replaceState(null, '', '/junior#module=failed-1');
  const { api, sessionApi } = apiWithModules([learnerModule({
    id: 'failed-1', status: 'failed', stage: 'publishing', error: 'Author-only generation error',
  })]);

  render(<App api={api} sessionApi={sessionApi} submissionApi={submissionApi} />);

  expect(await screen.findByText(/not available/i)).toBeInTheDocument();
  expect(screen.queryByText('Make webhook processing idempotent.')).not.toBeInTheDocument();
  expect(screen.queryByText('Author-only generation error')).not.toBeInTheDocument();
});

it('preserves senior access and existing module links from the home URL', async () => {
  window.history.replaceState(null, '', '/#module=ready-1');
  const { api, sessionApi } = apiWithModules();

  render(<App api={api} sessionApi={sessionApi} submissionApi={submissionApi} />);

  await waitFor(() => expect(window.location.pathname).toBe('/senior'));
  expect(window.location.hash).toBe('#module=ready-1');
  expect(await screen.findByText('Author verification diagnostics')).toBeInTheDocument();
});

it('recovers the junior catalog after a failed request', async () => {
  window.history.replaceState(null, '', '/junior');
  const { api, sessionApi, request } = apiWithModules();
  request.mockRejectedValueOnce(new Error('Network unavailable'));

  render(<App api={api} sessionApi={sessionApi} submissionApi={submissionApi} />);

  expect(await screen.findByRole('alert')).toHaveTextContent(/could not reach/i);
  fireEvent.click(screen.getByRole('button', { name: /try again/i }));
  expect(await screen.findByText('Webhook idempotency')).toBeInTheDocument();
});
