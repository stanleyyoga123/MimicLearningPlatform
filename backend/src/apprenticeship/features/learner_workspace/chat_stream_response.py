"""Serialize a chat turn as newline-delimited JSON and release it on disconnect."""

import json
from collections.abc import AsyncGenerator

from fastapi.responses import StreamingResponse
from starlette.types import Receive, Scope, Send

from apprenticeship.features.learner_workspace.chat_turn import ChatTurn


class ChatStreamResponse(StreamingResponse):
    def __init__(self, turn: ChatTurn):
        self._turn = turn
        self._body = self._lines()
        super().__init__(
            self._body,
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    async def _lines(self) -> AsyncGenerator[bytes, None]:
        events = self._turn.__aiter__()
        try:
            async for event in events:
                yield (json.dumps(event, separators=(",", ":")) + "\n").encode("utf-8")
        finally:
            await events.aclose()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._turn.close()
            await self._body.aclose()
