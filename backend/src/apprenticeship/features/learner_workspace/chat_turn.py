"""Own one streamed conversation turn and its temporary session reservation."""

import asyncio
from collections.abc import AsyncGenerator, Callable

from apprenticeship.clients.openrouter_client import (
    ChatMessage,
    OpenRouterFailure,
    OpenRouterTimeout,
)
from apprenticeship.features.learner_workspace.chat_session import ChatSession


MAX_HISTORY_MESSAGES = 24


class ChatTurn:
    def __init__(
        self,
        session: ChatSession,
        agent_id: str,
        user_content: str,
        source: AsyncGenerator[str, None],
        is_active: Callable[[], bool],
    ):
        self._session = session
        self._agent_id = agent_id
        self._user_content = user_content
        self._source = source
        self._is_active = is_active
        self._started = False
        self._closed = False

    def __aiter__(self) -> AsyncGenerator[dict[str, str | int], None]:
        return self._events()

    async def _events(self) -> AsyncGenerator[dict[str, str | int], None]:
        if self._started:
            raise RuntimeError("A conversation turn can only be consumed once")
        self._started = True
        if self._closed:
            return
        self._session.in_flight = asyncio.current_task()
        chunks: list[str] = []
        try:
            if not self._is_active():
                yield self._error("Workspace session has ended", 404)
                return
            async for chunk in self._source:
                if not self._is_active():
                    yield self._error("Workspace session has ended", 404)
                    return
                chunks.append(chunk)
                yield {"type": "delta", "agent_id": self._agent_id, "content": chunk}
            if not self._is_active():
                yield self._error("Workspace session has ended", 404)
                return
            reply = "".join(chunks)
            if not reply.strip():
                raise OpenRouterFailure("OpenRouter returned an empty reply. Try again.")
            yield {"type": "done", "agent_id": self._agent_id}
            if self._closed or not self._is_active():
                return
            history = self._session.histories[self._agent_id]
            history.extend([
                ChatMessage(role="user", content=self._user_content),
                ChatMessage(role="assistant", content=reply),
            ])
            if len(history) > MAX_HISTORY_MESSAGES:
                del history[:-MAX_HISTORY_MESSAGES]
        except OpenRouterTimeout as error:
            yield self._error(str(error), 504)
        except OpenRouterFailure as error:
            yield self._error(str(error), 502)
        except asyncio.CancelledError:
            if self._is_active():
                raise
            yield self._error("Workspace session has ended", 404)
        finally:
            await self._source.aclose()
            self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._session.reserved = False
        task = self._session.in_flight
        self._session.in_flight = None
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()

    def _error(self, detail: str, status: int) -> dict[str, str | int]:
        return {
            "type": "error",
            "agent_id": self._agent_id,
            "detail": detail,
            "status": status,
        }
