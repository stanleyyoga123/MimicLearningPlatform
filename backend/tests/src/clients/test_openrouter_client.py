"""OpenRouter streaming HTTP boundary and safe failure behavior."""

import asyncio
import json
from collections.abc import AsyncIterator

import httpx
import pytest

from apprenticeship.clients.openrouter_client import (
    ChatMessage,
    OpenRouterClient,
    OpenRouterFailure,
    OpenRouterTimeout,
)


class FragmentedStream(httpx.AsyncByteStream):
    def __init__(self, fragments: list[bytes]):
        self.fragments = fragments

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for fragment in self.fragments:
            yield fragment


async def collect(client: OpenRouterClient) -> list[str]:
    return [chunk async for chunk in client.stream([ChatMessage(role="user", content="Help")])]


def test_stream_sends_configured_model_and_yields_sse_text_in_order() -> None:
    seen: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        unicode_event = 'data: {"choices":[{"delta":{"content":"🙂"}}]}\r\n\r\n'.encode()
        split_at = unicode_event.index("🙂".encode()) + 1
        return httpx.Response(200, stream=FragmentedStream([
            b': keepalive\r\n\r\ndata: {"choices":[{"delta":{"role":"assistant"}}]}\r\n\r\n',
            b'data: {"choices": [\r\ndata: {"delta":{"content":"He',
            b'llo \\u2603"}}]}\r\n\r\n',
            unicode_event[:split_at], unicode_event[split_at:],
            b'data: {"choices":[]}\r\n\r\n',
            b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\r\n\r\n',
            b'data: [DONE]\r\n\r\n',
        ]))

    client = OpenRouterClient(
        api_key="local-secret", model="z-ai/glm-5.3-flash", transport=httpx.MockTransport(respond),
    )
    messages = [
        ChatMessage(role="system", content="Stay within the task"),
        ChatMessage(role="user", content="How do I start?"),
    ]

    chunks = asyncio.run(_collect_messages(client, messages))

    assert chunks == ["Hello ☃", "🙂"]
    assert len(seen) == 1
    assert seen[0].method == "POST"
    assert str(seen[0].url) == "https://openrouter.ai/api/v1/chat/completions"
    assert seen[0].headers["Authorization"] == "Bearer local-secret"
    assert json.loads(seen[0].read()) == {
        "model": "z-ai/glm-5.3-flash",
        "max_tokens": 2000,
        "stream": True,
        "messages": [
            {"role": "system", "content": "Stay within the task"},
            {"role": "user", "content": "How do I start?"},
        ],
    }


async def _collect_messages(client: OpenRouterClient, messages: list[ChatMessage]) -> list[str]:
    return [chunk async for chunk in client.stream(messages)]


def test_first_delta_arrives_before_provider_finishes() -> None:
    release = asyncio.Event()

    class PausedStream(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield b'data: {"choices":[{"delta":{"content":"First"}}]}\n\n'
            await release.wait()
            yield b'data: {"choices":[{"delta":{"content":" second"}}]}\n\n'
            yield b'data: [DONE]\n\n'

    client = OpenRouterClient(
        api_key="local-secret", model="z-ai/glm-5.3-flash",
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, stream=PausedStream())),
    )

    async def exercise() -> None:
        stream = client.stream([ChatMessage(role="user", content="Help")])
        assert await asyncio.wait_for(anext(stream), timeout=2) == "First"
        assert not release.is_set()
        release.set()
        assert [chunk async for chunk in stream] == [" second"]

    asyncio.run(exercise())


def test_stream_maps_timeout_to_safe_error() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret upstream detail", request=request)

    client = OpenRouterClient(
        api_key="local-secret", model="z-ai/glm-5.3-flash", transport=httpx.MockTransport(timeout),
    )

    with pytest.raises(OpenRouterTimeout) as error:
        asyncio.run(collect(client))

    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(502, json={"error": "upstream private detail"}),
        httpx.Response(200, text='data: {"error":{"message":"upstream private detail"}}\n\n'),
        httpx.Response(200, text='data: {not-json}\n\n'),
        httpx.Response(200, text='data: {"choices":[]}\n\n'),
        httpx.Response(200, text='data: [DONE]\n\n'),
        httpx.Response(200, text='data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'),
    ],
)
def test_stream_rejects_provider_failure_or_truncation_without_leaking_details(
    response: httpx.Response,
) -> None:
    client = OpenRouterClient(
        api_key="local-secret", model="z-ai/glm-5.3-flash",
        transport=httpx.MockTransport(lambda _request: response),
    )

    with pytest.raises(OpenRouterFailure) as error:
        asyncio.run(collect(client))

    assert "secret" not in str(error.value)
    assert "upstream private detail" not in str(error.value)
