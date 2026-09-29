"""HTTP operations for ephemeral junior workspace conversations."""

from fastapi import APIRouter, HTTPException

from apprenticeship.features.learner_workspace.chat_models import (
    ChatSessionView,
    SendMessageRequest,
)
from apprenticeship.features.learner_workspace.chat_stream_response import ChatStreamResponse
from apprenticeship.features.learner_workspace.chat_session_service import (
    ChatNotConfigured,
    ChatSessionService,
    ModuleUnavailable,
    SessionBusy,
    SessionNotFound,
)


def create_chat_router(service: ChatSessionService) -> APIRouter:
    router = APIRouter(tags=["learner workspace"])

    @router.post("/modules/{module_id}/sessions", response_model=ChatSessionView, status_code=201)
    async def create_session(module_id: str) -> ChatSessionView:
        try:
            return service.create(module_id)
        except SessionNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ModuleUnavailable as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ChatNotConfigured as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except SessionBusy as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.post("/sessions/{session_id}/messages")
    async def send_message(session_id: str, request: SendMessageRequest) -> ChatStreamResponse:
        try:
            turn = service.start_stream(session_id, request.agent_id, request.content)
            return ChatStreamResponse(turn)
        except SessionNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except SessionBusy as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ChatNotConfigured as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @router.post("/sessions/{session_id}/heartbeat", status_code=204)
    async def heartbeat(session_id: str) -> None:
        try:
            service.heartbeat(session_id)
        except SessionNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @router.post("/sessions/{session_id}/close", status_code=204)
    async def close_session(session_id: str) -> None:
        service.close(session_id)

    return router
