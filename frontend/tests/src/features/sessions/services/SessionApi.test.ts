import { expect, it, vi } from 'vitest';
import { SessionApi } from '../../../../../src/features/sessions/services/SessionApi';

function streamResponse(chunks: Uint8Array[]): Response {
  return new Response(new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(chunk);
      controller.close();
    },
  }), { headers: { 'Content-Type': 'application/x-ndjson' } });
}

it('renders decoded delta text before the terminal frame, across UTF-8 and line boundaries', async () => {
  const encoder = new TextEncoder();
  const first = encoder.encode('{"type":"delta","agent_id":"mentor","content":"Café"}\n');
  const accentedByte = first.indexOf(0xc3);
  const second = encoder.encode('{"type":"delta","agent_id":"mentor","content":" works"}\r\n{"type":"done","agent_id":"mentor"}\n');
  const request = vi.fn<typeof fetch>().mockResolvedValue(streamResponse([
    first.slice(0, accentedByte + 1),
    first.slice(accentedByte + 1),
    second.slice(0, 21),
    second.slice(21),
  ]));
  const api = new SessionApi('', request);
  const updates: string[] = [];

  const reply = await api.send('session-1', 'mentor', 'Question', new AbortController().signal, (partial) => updates.push(partial));

  expect(updates).toEqual(['Café', 'Café works']);
  expect(reply).toBe('Café works');
  expect(request).toHaveBeenCalledWith('/sessions/session-1/messages', expect.objectContaining({
    method: 'POST', body: JSON.stringify({ agent_id: 'mentor', content: 'Question' }),
  }));
});

it('rejects a stream error after partial text without treating it as a completed reply', async () => {
  const encoder = new TextEncoder();
  const request = vi.fn<typeof fetch>().mockResolvedValue(streamResponse([encoder.encode(
    '{"type":"delta","agent_id":"mentor","content":"Partial"}\n'
    + '{"type":"error","agent_id":"mentor","detail":"Provider timed out.","status":504}\n',
  )]));
  const updates: string[] = [];

  await expect(new SessionApi('', request).send('session-1', 'mentor', 'Question', new AbortController().signal, (partial) => updates.push(partial)))
    .rejects.toMatchObject({ name: 'SessionApiError', message: 'Provider timed out.', status: 504 });
  expect(updates).toEqual(['Partial']);
});

it('rejects premature EOF and an unexpected agent', async () => {
  const encoder = new TextEncoder();
  const incomplete = vi.fn<typeof fetch>().mockResolvedValue(streamResponse([
    encoder.encode('{"type":"delta","agent_id":"mentor","content":"Partial"}\n'),
  ]));
  const wrongAgent = vi.fn<typeof fetch>().mockResolvedValue(streamResponse([
    encoder.encode('{"type":"done","agent_id":"peer-0"}\n'),
  ]));

  await expect(new SessionApi('', incomplete).send('session-1', 'mentor', 'Question', new AbortController().signal, () => {}))
    .rejects.toThrow('ended unexpectedly');
  await expect(new SessionApi('', wrongAgent).send('session-1', 'mentor', 'Question', new AbortController().signal, () => {}))
    .rejects.toThrow('unexpected response');
});
