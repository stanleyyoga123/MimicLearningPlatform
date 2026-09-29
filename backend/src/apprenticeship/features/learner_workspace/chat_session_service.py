"""Manage temporary learner chat sessions without persistent transcripts."""

import time
from collections.abc import AsyncGenerator, Callable
from typing import Protocol
from uuid import uuid4

from apprenticeship.clients.openrouter_client import ChatMessage
from apprenticeship.features.learner_workspace.chat_materials_reader import (
    ChatMaterialsReader,
    ChatMaterialsUnavailable,
)
from apprenticeship.features.learner_workspace.chat_models import ChatSessionView
from apprenticeship.features.learner_workspace.chat_session import ChatSession
from apprenticeship.features.learner_workspace.chat_turn import ChatTurn
from apprenticeship.features.modules.module_repository import ModuleRepository


SESSION_TTL_SECONDS = 90
MAX_SESSIONS = 100
class ChatModel(Protocol):
    def stream(self, messages: list[ChatMessage]) -> AsyncGenerator[str, None]: ...


class SessionNotFound(Exception):
    pass


class SessionBusy(Exception):
    pass


class ModuleUnavailable(Exception):
    pass


class ChatNotConfigured(Exception):
    pass


class ChatSessionService:
    def __init__(
        self,
        repository: ModuleRepository,
        materials_reader: ChatMaterialsReader,
        chat_model: ChatModel | None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._repository = repository
        self._materials_reader = materials_reader
        self._chat_model = chat_model
        self._clock = clock
        self._sessions: dict[str, ChatSession] = {}

    def create(self, module_id: str) -> ChatSessionView:
        module = self._repository.get(module_id)
        if module is None:
            raise SessionNotFound("Module not found")
        if module.status != "completed" or not module.repository_url or module.spec is None:
            raise ModuleUnavailable("This module is not ready for a junior workspace")
        if self._chat_model is None:
            raise ChatNotConfigured("Set OPENROUTER_API_KEY in the API environment to enable chat")
        self.expire()
        if len(self._sessions) >= MAX_SESSIONS:
            raise SessionBusy("Too many open workspaces. Close another workspace and try again.")

        try:
            materials = self._materials_reader.read(module_id, module.spec, module.peers)
        except ChatMaterialsUnavailable as error:
            raise ModuleUnavailable(str(error)) from error
        session_id = uuid4().hex
        self._sessions[session_id] = ChatSession(
            id=session_id, module_id=module_id, agents=materials.agents,
            contexts=materials.contexts,
            expires_at=self._clock() + SESSION_TTL_SECONDS,
            histories={agent.id: [] for agent in materials.agents},
        )
        return ChatSessionView(
            id=session_id, module_id=module_id, agents=materials.agents,
            expires_in_seconds=SESSION_TTL_SECONDS,
        )

    def heartbeat(self, session_id: str) -> None:
        session = self._require(session_id)
        session.expires_at = self._clock() + SESSION_TTL_SECONDS

    def start_stream(self, session_id: str, agent_id: str, content: str) -> ChatTurn:
        session = self._require(session_id)
        if agent_id not in session.contexts:
            raise ValueError("Choose an available conversation agent")
        if session.reserved:
            raise SessionBusy("Another message is still in progress")
        if self._chat_model is None:
            raise ChatNotConfigured("Set OPENROUTER_API_KEY in the API environment to enable chat")
        history = session.histories[agent_id]
        messages = [
            ChatMessage(role="system", content=session.contexts[agent_id]),
            *history,
            ChatMessage(role="user", content=content),
        ]
        source = self._chat_model.stream(messages)
        turn = ChatTurn(
            session, agent_id, content, source,
            lambda: self._sessions.get(session_id) is session
            and session.expires_at > self._clock(),
        )
        session.reserved = True
        return turn

    def close(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is not None:
            session.cancel()

    def close_all(self) -> None:
        for session_id in list(self._sessions):
            self.close(session_id)

    def expire(self) -> None:
        now = self._clock()
        for session_id, session in list(self._sessions.items()):
            if session.expires_at <= now:
                self.close(session_id)

    def _require(self, session_id: str) -> ChatSession:
        self.expire()
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFound("Workspace session has ended")
        return session
