"""Ephemeral conversation state for one open learner workspace."""

import asyncio
from dataclasses import dataclass, field

from apprenticeship.clients.openrouter_client import ChatMessage
from apprenticeship.features.learner_workspace.chat_models import ChatAgent


@dataclass
class ChatSession:
    id: str
    module_id: str
    agents: list[ChatAgent]
    contexts: dict[str, str]
    expires_at: float
    histories: dict[str, list[ChatMessage]] = field(default_factory=dict)
    in_flight: asyncio.Task[object] | None = None
    reserved: bool = False

    def cancel(self) -> None:
        if self.in_flight is not None and not self.in_flight.done():
            self.in_flight.cancel()
        self.reserved = False
