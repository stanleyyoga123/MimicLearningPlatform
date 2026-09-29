import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { App } from '../../../src/app/App';
import { ModuleApi } from '../../../src/features/modules/services/ModuleApi';
import { SessionApi } from '../../../src/features/sessions/services/SessionApi';
import { SubmissionApi } from '../../../src/features/submissions/services/SubmissionApi';
import { learnerModule } from '../../fixtures/modules/learnerModule';

const sessionResponse = {
  id: 'session-1', module_id: 'ready-1', expires_in_seconds: 90,
  agents: [
    { id: 'peer-0', name: 'Maya', role: 'Backend teammate', description: 'Knows the order endpoint.' },
    { id: 'peer-1', name: 'Noah', role: 'QA teammate', description: 'Knows reproduction steps.' },
    { id: 'mentor', name: 'Mentor', role: 'Mentor', description: 'Guides your approach.' },
  ],
};

afterEach(() => window.history.replaceState(null, '', '/'));

function response(data: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(data), { status });
}

function streamedReply(agentId: string, content: string): Response {
  return new Response(
    `${JSON.stringify({ type: 'delta', agent_id: agentId, content })}\n${JSON.stringify({ type: 'done', agent_id: agentId })}\n`,
    { headers: { 'Content-Type': 'application/x-ndjson' } },
  );
}

function renderWorkspace(request: typeof fetch) {
  window.history.replaceState(null, '', '/junior#module=ready-1');
  const submissionApi = new SubmissionApi('', vi.fn<typeof fetch>().mockResolvedValue(response([])));
  return render(<App api={new ModuleApi('', request)} sessionApi={new SessionApi('', request)} submissionApi={submissionApi} />);
}

it('keeps conversations separate by teammate and discards them when the workspace closes', async () => {
  let starts = 0;
  const request = vi.fn<typeof fetch>().mockImplementation(async (input, options) => {
    const path = String(input);
    if (path === '/modules') return response([learnerModule()]);
    if (path === '/modules/ready-1/sessions') return response({ ...sessionResponse, id: `session-${++starts}` }, 201);
    if (path.endsWith('/messages')) {
      const body = JSON.parse(String(options?.body)) as { agent_id: string; content: string };
      return streamedReply(body.agent_id, `${body.agent_id}: ${body.content}`);
    }
    if (path.endsWith('/close')) return response(null, 204);
    return response({ detail: 'Unexpected request' }, 404);
  });

  renderWorkspace(request);
  fireEvent.click(await screen.findByRole('button', { name: /start task/i }));
  expect(await screen.findByRole('heading', { name: 'Conversation' })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /mentor/i })).toBeInTheDocument();

  fireEvent.change(screen.getByRole('textbox', { name: /message maya/i }), { target: { value: 'Why duplicate orders?' } });
  fireEvent.click(screen.getByRole('button', { name: /send message/i }));
  await waitFor(() => expect(screen.getByRole('textbox', { name: /message maya/i })).toHaveValue(''));
  expect(within(screen.getByRole('log', { name: /maya/i })).getByText('peer-0: Why duplicate orders?')).toBeInTheDocument();

  fireEvent.click(screen.getByRole('tab', { name: /noah/i }));
  expect(within(screen.getByRole('log', { name: /noah/i })).queryByText('Why duplicate orders?')).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole('textbox', { name: /message noah/i }), { target: { value: 'How do I reproduce it?' } });
  fireEvent.click(screen.getByRole('button', { name: /send message/i }));
  await waitFor(() => expect(screen.getByRole('textbox', { name: /message noah/i })).toHaveValue(''));
  expect(within(screen.getByRole('log', { name: /noah/i })).getByText('peer-1: How do I reproduce it?')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab', { name: /maya/i }));
  expect(within(screen.getByRole('log', { name: /maya/i })).getByText('peer-0: Why duplicate orders?')).toBeInTheDocument();
  expect(within(screen.getByRole('log', { name: /maya/i })).queryByText('peer-1: How do I reproduce it?')).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /close workspace/i }));
  await waitFor(() => expect(request).toHaveBeenCalledWith('/sessions/session-1/close', { method: 'POST' }));
  expect(screen.queryByRole('heading', { name: 'Conversation' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /start task/i }));
  expect(await screen.findByRole('heading', { name: 'Conversation' })).toBeInTheDocument();
  expect(within(screen.getByRole('log', { name: /maya/i })).queryByText('peer-0: Why duplicate orders?')).not.toBeInTheDocument();
  expect(starts).toBe(2);
});

it('closes a session that finishes starting after the learner leaves the workspace', async () => {
  let resolveStart!: (value: Response) => void;
  const pendingStart = new Promise<Response>((resolve) => { resolveStart = resolve; });
  const request = vi.fn<typeof fetch>().mockImplementation(async (input) => {
    const path = String(input);
    if (path === '/modules') return response([learnerModule()]);
    if (path === '/modules/ready-1/sessions') return pendingStart;
    if (path.endsWith('/close')) return response(null, 204);
    return response({ detail: 'Unexpected request' }, 404);
  });

  renderWorkspace(request);
  fireEvent.click(await screen.findByRole('button', { name: /start task/i }));
  expect(await screen.findByText('Setting up your team…')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /close workspace/i }));
  resolveStart(response(sessionResponse, 201));

  await waitFor(() => expect(request).toHaveBeenCalledWith('/sessions/session-1/close', { method: 'POST' }));
  expect(screen.getByRole('button', { name: /start task/i })).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'Conversation' })).not.toBeInTheDocument();
});

it('closes a session created after the page unmounts during startup', async () => {
  let resolveStart!: (value: Response) => void;
  const pendingStart = new Promise<Response>((resolve) => { resolveStart = resolve; });
  const request = vi.fn<typeof fetch>().mockImplementation(async (input) => {
    const path = String(input);
    if (path === '/modules') return response([learnerModule()]);
    if (path === '/modules/ready-1/sessions') return pendingStart;
    if (path.endsWith('/close')) return response(null, 204);
    return response({ detail: 'Unexpected request' }, 404);
  });

  const page = renderWorkspace(request);
  fireEvent.click(await screen.findByRole('button', { name: /start task/i }));
  expect(await screen.findByText('Setting up your team…')).toBeInTheDocument();
  page.unmount();
  resolveStart(response(sessionResponse, 201));

  await waitFor(() => expect(request).toHaveBeenCalledWith('/sessions/session-1/close', { method: 'POST' }));
});

it('retains a draft after a provider error, then retries the message successfully', async () => {
  let messageAttempts = 0;
  const request = vi.fn<typeof fetch>().mockImplementation(async (input, options) => {
    const path = String(input);
    if (path === '/modules') return response([learnerModule()]);
    if (path === '/modules/ready-1/sessions') return response(sessionResponse, 201);
    if (path.endsWith('/messages')) {
      messageAttempts += 1;
      if (messageAttempts === 1) return response({ detail: 'The assistant is temporarily unavailable.' }, 502);
      const body = JSON.parse(String(options?.body)) as { agent_id: string; content: string };
      return streamedReply(body.agent_id, 'Try the existing order lookup.');
    }
    if (path.endsWith('/close')) return response(null, 204);
    return response({ detail: 'Unexpected request' }, 404);
  });

  renderWorkspace(request);
  fireEvent.click(await screen.findByRole('button', { name: /start task/i }));
  const composer = await screen.findByRole('textbox', { name: /message maya/i });
  fireEvent.change(composer, { target: { value: 'Here is my traceback' } });
  fireEvent.click(screen.getByRole('button', { name: /send message/i }));
  expect(await screen.findByRole('alert')).toHaveTextContent('The assistant is temporarily unavailable.');
  expect(composer).toHaveValue('Here is my traceback');
  fireEvent.click(screen.getByRole('button', { name: /send message/i }));
  await waitFor(() => expect(composer).toHaveValue(''));
  expect(screen.getByText('Try the existing order lookup.')).toBeInTheDocument();
  expect(messageAttempts).toBe(2);
});

it('shows reply text as it streams and commits one turn only after completion', async () => {
  let streamController!: ReadableStreamDefaultController<Uint8Array>;
  const encoder = new TextEncoder();
  const request = vi.fn<typeof fetch>().mockImplementation(async (input) => {
    const path = String(input);
    if (path === '/modules') return response([learnerModule()]);
    if (path === '/modules/ready-1/sessions') return response(sessionResponse, 201);
    if (path.endsWith('/messages')) return new Response(new ReadableStream<Uint8Array>({
      start(controller) { streamController = controller; },
    }), { headers: { 'Content-Type': 'application/x-ndjson' } });
    return response({ detail: 'Unexpected request' }, 404);
  });

  renderWorkspace(request);
  fireEvent.click(await screen.findByRole('button', { name: /start task/i }));
  const composer = await screen.findByRole('textbox', { name: /message maya/i });
  fireEvent.change(composer, { target: { value: 'How should I debug this?' } });
  fireEvent.click(screen.getByRole('button', { name: /send message/i }));
  expect(within(screen.getByRole('log', { name: /maya/i })).getByText('How should I debug this?')).toBeInTheDocument();
  expect(composer).toHaveValue('How should I debug this?');

  await act(async () => { streamController.enqueue(encoder.encode('{"type":"delta","agent_id":"peer-0","content":"Check the"}\n')); });
  expect(screen.getByText('Check the')).toBeInTheDocument();
  expect(screen.getByText(/maya is responding/i)).toBeInTheDocument();
  await act(async () => { streamController.enqueue(encoder.encode('{"type":"delta","agent_id":"peer-0","content":" logs."}\n')); });
  expect(screen.getByText('Check the logs.')).toBeInTheDocument();
  expect(composer).toHaveValue('How should I debug this?');

  await act(async () => {
    streamController.enqueue(encoder.encode('{"type":"done","agent_id":"peer-0"}\n'));
    streamController.close();
  });
  await waitFor(() => expect(composer).toHaveValue(''));
  expect(within(screen.getByRole('log', { name: /maya/i })).getAllByText('How should I debug this?')).toHaveLength(1);
  expect(within(screen.getByRole('log', { name: /maya/i })).getAllByText('Check the logs.')).toHaveLength(1);
});

it('clears an incomplete streamed reply while preserving the draft for retry', async () => {
  let streamController!: ReadableStreamDefaultController<Uint8Array>;
  const encoder = new TextEncoder();
  const request = vi.fn<typeof fetch>().mockImplementation(async (input) => {
    const path = String(input);
    if (path === '/modules') return response([learnerModule()]);
    if (path === '/modules/ready-1/sessions') return response(sessionResponse, 201);
    if (path.endsWith('/messages')) return new Response(new ReadableStream<Uint8Array>({
      start(controller) { streamController = controller; },
    }), { headers: { 'Content-Type': 'application/x-ndjson' } });
    return response({ detail: 'Unexpected request' }, 404);
  });

  renderWorkspace(request);
  fireEvent.click(await screen.findByRole('button', { name: /start task/i }));
  const composer = await screen.findByRole('textbox', { name: /message maya/i });
  fireEvent.change(composer, { target: { value: 'What failed?' } });
  fireEvent.click(screen.getByRole('button', { name: /send message/i }));
  await act(async () => { streamController.enqueue(encoder.encode('{"type":"delta","agent_id":"peer-0","content":"Partial answer"}\n')); });
  expect(screen.getByText('Partial answer')).toBeInTheDocument();

  await act(async () => {
    streamController.enqueue(encoder.encode('{"type":"error","agent_id":"peer-0","detail":"Provider timed out.","status":504}\n'));
    streamController.close();
  });
  expect(await screen.findByRole('alert')).toHaveTextContent('Provider timed out.');
  expect(composer).toHaveValue('What failed?');
  expect(screen.queryByText('Partial answer')).not.toBeInTheDocument();
  expect(within(screen.getByRole('log', { name: /maya/i })).queryByText('What failed?')).not.toBeInTheDocument();
});

it('shows an ended session on expiry without silently starting another one', async () => {
  let starts = 0;
  const request = vi.fn<typeof fetch>().mockImplementation(async (input) => {
    const path = String(input);
    if (path === '/modules') return response([learnerModule()]);
    if (path === '/modules/ready-1/sessions') { starts += 1; return response(sessionResponse, 201); }
    if (path.endsWith('/messages')) return response({ detail: 'Session expired.' }, 404);
    if (path.endsWith('/close')) return response(null, 204);
    return response({ detail: 'Unexpected request' }, 404);
  });

  renderWorkspace(request);
  fireEvent.click(await screen.findByRole('button', { name: /start task/i }));
  fireEvent.change(await screen.findByRole('textbox', { name: /message maya/i }), { target: { value: 'Hello' } });
  fireEvent.click(screen.getByRole('button', { name: /send message/i }));
  expect(await screen.findByText('Conversation ended')).toBeInTheDocument();
  expect(starts).toBe(1);
  fireEvent.click(screen.getByRole('button', { name: /start a new session/i }));
  expect(await screen.findByRole('heading', { name: 'Conversation' })).toBeInTheDocument();
  expect(starts).toBe(2);
});

it('aborts a pending reply on close and sends an unload close request on pagehide', async () => {
  const pendingSignals: AbortSignal[] = [];
  const request = vi.fn<typeof fetch>().mockImplementation(async (input, options) => {
    const path = String(input);
    if (path === '/modules') return response([learnerModule()]);
    if (path === '/modules/ready-1/sessions') return response(sessionResponse, 201);
    if (path.endsWith('/messages')) {
      if (options?.signal) pendingSignals.push(options.signal);
      return new Promise<Response>(() => {});
    }
    if (path.endsWith('/close')) return response(null, 204);
    return response({ detail: 'Unexpected request' }, 404);
  });

  renderWorkspace(request);
  fireEvent.click(await screen.findByRole('button', { name: /start task/i }));
  fireEvent.change(await screen.findByRole('textbox', { name: /message maya/i }), { target: { value: 'Can you help?' } });
  fireEvent.click(screen.getByRole('button', { name: /send message/i }));
  expect(await screen.findByText(/maya is thinking/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /close workspace/i }));
  expect(pendingSignals[0]?.aborted).toBe(true);
  await waitFor(() => expect(request).toHaveBeenCalledWith('/sessions/session-1/close', { method: 'POST' }));

  fireEvent.click(screen.getByRole('button', { name: /start task/i }));
  expect(await screen.findByRole('heading', { name: 'Conversation' })).toBeInTheDocument();
  fireEvent(window, new Event('pagehide'));
  expect(await screen.findByText('Conversation ended')).toBeInTheDocument();
  expect(request).toHaveBeenCalledWith('/sessions/session-1/close', { method: 'POST', keepalive: true });
});
