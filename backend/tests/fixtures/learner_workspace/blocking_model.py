"""Controlled chat model for concurrent request and cancellation tests."""

import asyncio

from apprenticeship.clients.openrouter_client import ChatMessage


class BlockingModel:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def stream(self, _messages: list[ChatMessage]):
        self.started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise
        yield "unreachable"
