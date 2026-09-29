"""An interrupted HTTP stream closes its provider and releases the session."""

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from starlette.requests import ClientDisconnect

from apprenticeship.clients.openrouter_client import ChatMessage
from apprenticeship.features.learner_workspace.chat_materials_reader import ChatMaterialsReader
from apprenticeship.features.learner_workspace.chat_session_service import ChatSessionService
from apprenticeship.features.learner_workspace.chat_stream_response import ChatStreamResponse
from apprenticeship.features.modules.module_repository import ModuleRepository
from tests.fixtures.learner_workspace.published_module import published_module


@pytest.mark.parametrize("failed_event", ["delta", "done"])
def test_asgi_send_failure_does_not_commit_history_and_releases_busy_slot(
    tmp_path: Path, failed_event: str,
) -> None:
    module_id = published_module(tmp_path)

    class ObservableModel:
        def __init__(self) -> None:
            self.closed = asyncio.Event()
            self.calls: list[list[ChatMessage]] = []

        async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
            self.calls.append([message.model_copy() for message in messages])
            if len(self.calls) == 2:
                yield "Retry works"
                return
            try:
                yield "First delta"
                if failed_event == "delta":
                    await asyncio.Event().wait()
            finally:
                self.closed.set()

    async def exercise() -> None:
        model = ObservableModel()
        service = ChatSessionService(
            ModuleRepository(tmp_path / "modules.sqlite3"), ChatMaterialsReader(tmp_path), model,
        )
        session_id = service.create(module_id).id
        response = ChatStreamResponse(service.start_stream(session_id, "mentor", "Question"))
        attempted_event: str | None = None

        async def receive() -> dict[str, str]:
            await asyncio.Event().wait()
            return {"type": "http.disconnect"}

        async def send(message: dict[str, object]) -> None:
            nonlocal attempted_event
            if message["type"] == "http.response.body" and message.get("body"):
                event = json.loads(bytes(message["body"]).decode())
                if event["type"] == failed_event:
                    attempted_event = event["type"]
                    raise OSError("client connection closed")

        scope = {
            "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
            "method": "POST", "path": f"/sessions/{session_id}/messages",
        }
        with pytest.raises(ClientDisconnect):
            await response(scope, receive, send)
        assert attempted_event == failed_event
        assert model.closed.is_set()

        retry = service.start_stream(session_id, "mentor", "Retry question")
        assert [event async for event in retry] == [
            {"type": "delta", "agent_id": "mentor", "content": "Retry works"},
            {"type": "done", "agent_id": "mentor"},
        ]
        assert [message.role for message in model.calls[1]] == ["system", "user"]
        assert model.calls[1][-1].content == "Retry question"
        retry.close()

    asyncio.run(exercise())
