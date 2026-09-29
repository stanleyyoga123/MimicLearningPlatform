"""Webhook-only HTTP surface for a tunnel; authoring and chat stay on the local API."""

from fastapi import FastAPI

from apprenticeship.config.settings import Settings
from apprenticeship.features.github_webhooks.github_webhook_service import GitHubWebhookService
from apprenticeship.features.github_webhooks.webhook_inbox_repository import WebhookInboxRepository
from apprenticeship.features.github_webhooks.webhook_routes import create_webhook_router
from apprenticeship.features.modules.module_repository import ModuleRepository


def create_webhook_app(settings: Settings) -> FastAPI:
    database = settings.data_dir / "modules.sqlite3"
    service = GitHubWebhookService(
        settings.github_webhook_secret, WebhookInboxRepository(database), ModuleRepository(database),
    )
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.include_router(create_webhook_router(service))
    return app


def create_default_webhook_app() -> FastAPI:
    return create_webhook_app(Settings.from_environment())
