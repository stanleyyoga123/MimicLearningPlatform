from fastapi import APIRouter, HTTPException, Request, Response

from apprenticeship.features.github_webhooks.github_webhook_service import (
    MAX_WEBHOOK_BYTES,
    GitHubWebhookService,
    WebhookError,
)
from apprenticeship.features.github_webhooks.webhook_event import WebhookEvent
from apprenticeship.features.github_webhooks.webhook_inbox_repository import WebhookInboxRepository


def create_webhook_router(service: GitHubWebhookService) -> APIRouter:
    router = APIRouter()

    @router.post("/webhooks/github")
    async def receive_github_webhook(request: Request, response: Response) -> dict[str, str]:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_WEBHOOK_BYTES:
                    raise HTTPException(status_code=413, detail="GitHub webhook payload exceeds 2 MB")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid Content-Length") from None
        chunks = bytearray()
        async for chunk in request.stream():
            if len(chunks) + len(chunk) > MAX_WEBHOOK_BYTES:
                raise HTTPException(status_code=413, detail="GitHub webhook payload exceeds 2 MB")
            chunks.extend(chunk)
        try:
            status_code, message = service.ingest(
                bytes(chunks), request.headers.get("x-hub-signature-256"),
                request.headers.get("x-github-delivery"), request.headers.get("x-github-event"),
            )
        except WebhookError as error:
            raise HTTPException(status_code=error.status_code, detail=str(error)) from error
        response.status_code = status_code
        return {"status": message}

    return router


def create_webhook_admin_router(inbox: WebhookInboxRepository) -> APIRouter:
    router = APIRouter()

    @router.get("/webhooks/github/deliveries", response_model=list[WebhookEvent])
    def list_deliveries() -> list[WebhookEvent]:
        return inbox.list_recent()

    @router.post("/webhooks/github/deliveries/{delivery_id}/retry", response_model=WebhookEvent)
    def retry_delivery(delivery_id: str) -> WebhookEvent:
        try:
            event = inbox.retry(delivery_id)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if event is None:
            raise HTTPException(status_code=404, detail="Webhook delivery not found")
        return event

    return router
