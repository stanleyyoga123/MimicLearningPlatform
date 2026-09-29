import asyncio
import time
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from apprenticeship.config.settings import Settings
from apprenticeship.clients.openrouter_client import OpenRouterClient
from apprenticeship.clients.github_review_client import GitHubReviewClient
from apprenticeship.clients.github_app_client import GitHubAppClient
from apprenticeship.features.learner_workspace.chat_materials_reader import ChatMaterialsReader
from apprenticeship.features.learner_workspace.chat_routes import create_chat_router
from apprenticeship.features.learner_workspace.chat_session_service import (
    ChatModel,
    ChatSessionService,
)
from apprenticeship.features.modules.module_repository import ModuleRepository
from apprenticeship.features.modules.module_routes import create_module_router
from apprenticeship.features.modules.module_service import ModuleService
from apprenticeship.features.submissions.submission_repository import SubmissionRepository
from apprenticeship.features.submissions.submission_routes import create_submission_router
from apprenticeship.features.submissions.submission_service import SubmissionService
from apprenticeship.features.github_webhooks.github_webhook_service import GitHubWebhookService
from apprenticeship.features.github_webhooks.webhook_inbox_repository import WebhookInboxRepository
from apprenticeship.features.github_webhooks.webhook_routes import (
    create_webhook_router,
    create_webhook_admin_router,
)


def create_app(
    settings: Settings,
    chat_client: ChatModel | None = None,
    chat_clock: Callable[[], float] = time.monotonic,
    review_client: GitHubReviewClient | None = None,
) -> FastAPI:
    repository = ModuleRepository(settings.data_dir / "modules.sqlite3")
    service = ModuleService(repository, settings.data_dir)
    model = chat_client or (
        OpenRouterClient(settings.openrouter_api_key, settings.openrouter_model)
        if settings.openrouter_api_key else None
    )
    materials_reader = ChatMaterialsReader(settings.data_dir)
    chat_service = ChatSessionService(repository, materials_reader, model, chat_clock)
    github_app = (
        GitHubAppClient(settings.github_app_id, settings.github_app_private_key_path)
        if settings.github_app_id and settings.github_app_private_key_path else None
    )
    reviewer = review_client or (GitHubReviewClient(github_app) if github_app else None)
    submissions = SubmissionService(
        SubmissionRepository(settings.data_dir / "modules.sqlite3"), repository, reviewer,
    )
    webhook_inbox = WebhookInboxRepository(settings.data_dir / "modules.sqlite3")
    webhooks = GitHubWebhookService(settings.github_webhook_secret, webhook_inbox, repository)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        async def sweep_expired() -> None:
            while True:
                await asyncio.sleep(15)
                chat_service.expire()

        sweep_task = asyncio.create_task(sweep_expired())
        try:
            yield
        finally:
            sweep_task.cancel()
            await asyncio.gather(sweep_task, return_exceptions=True)
            chat_service.close_all()

    app = FastAPI(title="Mimic", lifespan=lifespan)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "testserver"],
    )
    allowed_origins = {
        settings.cors_origin,
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    }

    @app.middleware("http")
    async def protect_mutations(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and origin and origin not in allowed_origins:
            return JSONResponse(status_code=403, content={"detail": "Origin is not allowed"})
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(allowed_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(create_module_router(service))
    app.include_router(create_chat_router(chat_service))
    app.include_router(create_submission_router(submissions))
    app.include_router(create_webhook_router(webhooks))
    app.include_router(create_webhook_admin_router(webhook_inbox))
    return app


def create_default_app() -> FastAPI:
    return create_app(Settings.from_environment())
