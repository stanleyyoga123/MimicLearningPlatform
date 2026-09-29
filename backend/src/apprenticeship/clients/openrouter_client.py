"""OpenRouter streaming chat boundary for temporary learner sessions."""

import asyncio
from collections.abc import AsyncIterator

import httpx
from pydantic import BaseModel, ValidationError


MAX_EVENT_CHARS = 100_000
MAX_REPLY_CHARS = 100_000


class ChatMessage(BaseModel):
    role: str
    content: str


class _Delta(BaseModel):
    content: str | None = None


class _StreamChoice(BaseModel):
    delta: _Delta
    finish_reason: str | None = None


class _StreamFrame(BaseModel):
    choices: list[_StreamChoice] | None = None
    error: dict[str, object] | None = None


class OpenRouterFailure(Exception):
    pass


class OpenRouterTimeout(OpenRouterFailure):
    pass


class OpenRouterClient:
    def __init__(self, api_key: str, model: str, transport: httpx.AsyncBaseTransport | None = None):
        self._api_key = api_key
        self._model = model
        self._transport = transport

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        try:
            async with asyncio.timeout(60):
                async with httpx.AsyncClient(timeout=60, transport=self._transport) as client:
                    async with client.stream(
                        "POST",
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {self._api_key}"},
                        json={
                            "model": self._model,
                            "max_tokens": 2000,
                            "stream": True,
                            "messages": [item.model_dump() for item in messages],
                        },
                    ) as response:
                        response.raise_for_status()
                        async for chunk in self._read_events(response):
                            yield chunk
        except (TimeoutError, httpx.TimeoutException) as error:
            raise OpenRouterTimeout("OpenRouter timed out. Try sending the message again.") from error
        except (httpx.HTTPError, ValueError, ValidationError, UnicodeError) as error:
            raise OpenRouterFailure("OpenRouter could not complete the message. Try again.") from error

    async def _read_events(self, response: httpx.Response) -> AsyncIterator[str]:
        data_lines: list[str] = []
        event_chars = 0
        reply_chars = 0
        saw_content = False
        async for line in response.aiter_lines():
            if line == "":
                if not data_lines:
                    continue
                data = "\n".join(data_lines)
                if data == "[DONE]":
                    if not saw_content:
                        raise OpenRouterFailure("OpenRouter returned an empty reply. Try again.")
                    return
                try:
                    frame = _StreamFrame.model_validate_json(data)
                except ValidationError as error:
                    raise OpenRouterFailure("OpenRouter returned an invalid stream. Try again.") from error
                if frame.error is not None or frame.choices is None:
                    raise OpenRouterFailure("OpenRouter could not complete the message. Try again.")
                for choice in frame.choices:
                    if choice.finish_reason not in (None, "stop"):
                        raise OpenRouterFailure("OpenRouter could not complete the message. Try again.")
                    content = choice.delta.content
                    if content:
                        reply_chars += len(content)
                        if reply_chars > MAX_REPLY_CHARS:
                            raise OpenRouterFailure("OpenRouter reply was too long. Try again.")
                        saw_content = True
                        yield content
                data_lines = []
                event_chars = 0
                continue
            if line.startswith(":"):
                continue
            field, separator, value = line.partition(":")
            if field != "data" or not separator:
                continue
            data_lines.append(value[1:] if value.startswith(" ") else value)
            event_chars += len(line)
            if event_chars > MAX_EVENT_CHARS:
                raise OpenRouterFailure("OpenRouter returned an invalid stream. Try again.")
        raise OpenRouterFailure("OpenRouter stream ended unexpectedly. Try again.")
