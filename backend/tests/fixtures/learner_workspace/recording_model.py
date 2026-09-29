"""Controlled chat model that captures each provider request."""

from apprenticeship.clients.openrouter_client import ChatMessage


class RecordingModel:
    def __init__(self, outcomes: list[list[str | Exception] | Exception] | None = None) -> None:
        self.calls: list[list[ChatMessage]] = []
        self.outcomes = outcomes or []

    async def stream(self, messages: list[ChatMessage]):
        self.calls.append([message.model_copy() for message in messages])
        outcome = self.outcomes.pop(0) if self.outcomes else ["Try the duplicate delivery test."]
        if isinstance(outcome, Exception):
            raise outcome
        for item in outcome:
            if isinstance(item, Exception):
                raise item
            yield item
