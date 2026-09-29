"""Chat turn lifecycle and history at the streaming service boundary."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from apprenticeship.clients.openrouter_client import ChatMessage
from apprenticeship.features.learner_workspace.chat_materials_reader import ChatMaterialsReader
from apprenticeship.features.learner_workspace.chat_session_service import ChatSessionService, SessionBusy
from apprenticeship.features.modules.module_repository import ModuleRepository
from tests.fixtures.learner_workspace.published_module import published_module


def test_first_delta_is_available_before_completion_and_history_commits_after_done(
    tmp_path: Path,
) -> None:
    module_id = published_module(tmp_path)

    class PausedModel:
        def __init__(self) -> None:
            self.release = asyncio.Event()
            self.calls: list[list[ChatMessage]] = []

        async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
            self.calls.append([message.model_copy() for message in messages])
            yield "First"
            await self.release.wait()
            yield " answer"

    async def exercise() -> None:
        model = PausedModel()
        service = ChatSessionService(
            ModuleRepository(tmp_path / "modules.sqlite3"), ChatMaterialsReader(tmp_path), model,
        )
        session_id = service.create(module_id).id
        turn = service.start_stream(session_id, "mentor", "Question")
        iterator = turn.__aiter__()
        first = await asyncio.wait_for(anext(iterator), timeout=2)
        assert first == {"type": "delta", "agent_id": "mentor", "content": "First"}
        assert not model.release.is_set()
        with pytest.raises(SessionBusy):
            service.start_stream(session_id, "mentor", "Concurrent")

        model.release.set()
        assert [event async for event in iterator] == [
            {"type": "delta", "agent_id": "mentor", "content": " answer"},
            {"type": "done", "agent_id": "mentor"},
        ]
        turn.close()
        followup = service.start_stream(session_id, "mentor", "Followup")
        followup_iterator = followup.__aiter__()
        assert await anext(followup_iterator) == {
            "type": "delta", "agent_id": "mentor", "content": "First",
        }
        assert [message.role for message in model.calls[1]] == [
            "system", "user", "assistant", "user",
        ]
        assert model.calls[1][2].content == "First answer"
        await followup_iterator.aclose()
        followup.close()

    asyncio.run(exercise())


def test_aborting_after_first_delta_releases_slot_without_committing_partial_history(
    tmp_path: Path,
) -> None:
    module_id = published_module(tmp_path)

    class AbortableModel:
        def __init__(self) -> None:
            self.calls: list[list[ChatMessage]] = []
            self.closed = asyncio.Event()

        async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
            self.calls.append([message.model_copy() for message in messages])
            if len(self.calls) == 2:
                yield "Retry works"
                return
            try:
                yield "Partial"
                await asyncio.Event().wait()
            finally:
                self.closed.set()

    async def exercise() -> None:
        model = AbortableModel()
        service = ChatSessionService(
            ModuleRepository(tmp_path / "modules.sqlite3"), ChatMaterialsReader(tmp_path), model,
        )
        session_id = service.create(module_id).id
        turn = service.start_stream(session_id, "mentor", "First question")
        iterator = turn.__aiter__()
        assert await asyncio.wait_for(anext(iterator), timeout=2) == {
            "type": "delta", "agent_id": "mentor", "content": "Partial",
        }
        await iterator.aclose()
        turn.close()
        assert model.closed.is_set()

        retry = service.start_stream(session_id, "mentor", "Retry question")
        assert [event async for event in retry] == [
            {"type": "delta", "agent_id": "mentor", "content": "Retry works"},
            {"type": "done", "agent_id": "mentor"},
        ]
        assert [message.role for message in model.calls[1]] == ["system", "user"]
        retry.close()

    asyncio.run(exercise())


def test_unconsumed_turn_can_be_closed_and_retried(tmp_path: Path) -> None:
    module_id = published_module(tmp_path)

    class SimpleModel:
        async def stream(self, _messages: list[ChatMessage]) -> AsyncIterator[str]:
            yield "Ready"

    async def exercise() -> None:
        service = ChatSessionService(
            ModuleRepository(tmp_path / "modules.sqlite3"), ChatMaterialsReader(tmp_path),
            SimpleModel(),
        )
        session_id = service.create(module_id).id
        unused = service.start_stream(session_id, "mentor", "First")
        with pytest.raises(SessionBusy):
            service.start_stream(session_id, "mentor", "Concurrent")
        unused.close()
        retry = service.start_stream(session_id, "mentor", "Retry")
        assert [event async for event in retry][-1] == {"type": "done", "agent_id": "mentor"}
        retry.close()

    asyncio.run(exercise())
