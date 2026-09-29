import hashlib
import hmac
import json
import re

from pydantic import ValidationError

from apprenticeship.features.github_webhooks.webhook_inbox_repository import WebhookInboxRepository
from apprenticeship.features.github_webhooks.webhook_payload import WebhookPayload
from apprenticeship.features.modules.module_repository import ModuleRepository


_DELIVERY_ID = re.compile(r"[A-Za-z0-9-]{1,100}\Z")
_SIGNATURE = re.compile(r"sha256=([a-fA-F0-9]{64})\Z")
_ACTIONS = frozenset({"opened", "reopened", "ready_for_review", "synchronize"})
MAX_WEBHOOK_BYTES = 2_000_000


class WebhookError(ValueError):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class GitHubWebhookService:
    def __init__(self, secret: str | None, inbox: WebhookInboxRepository,
                 modules: ModuleRepository):
        self._secret = secret
        self._inbox = inbox
        self._modules = modules

    def ingest(self, raw: bytes, signature: str | None, delivery_id: str | None,
               event: str | None) -> tuple[int, str]:
        if not self._secret:
            raise WebhookError("GitHub webhook is not configured", 503)
        if len(raw) > MAX_WEBHOOK_BYTES:
            raise WebhookError("GitHub webhook payload exceeds 2 MB", 413)
        match = _SIGNATURE.fullmatch(signature or "")
        if match is None:
            raise WebhookError("Invalid GitHub webhook signature", 401)
        expected = hmac.new(self._secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(match.group(1).lower(), expected):
            raise WebhookError("Invalid GitHub webhook signature", 401)
        if not delivery_id or not _DELIVERY_ID.fullmatch(delivery_id):
            raise WebhookError("Invalid GitHub delivery ID", 422)
        if not event or len(event) > 100:
            raise WebhookError("Invalid GitHub event type", 422)
        if event == "ping":
            return 200, "GitHub webhook is ready"
        if event != "pull_request":
            return 200, "Event ignored"
        try:
            body = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise WebhookError("Invalid GitHub pull request event", 422) from None
        if not isinstance(body, dict):
            raise WebhookError("Invalid GitHub pull request event", 422)
        if body.get("action") not in _ACTIONS:
            return 200, "Pull request action ignored"
        try:
            payload = WebhookPayload.model_validate(body)
        except ValidationError:
            raise WebhookError("Invalid GitHub pull request event", 422) from None
        pull = payload.pull_request
        repository = payload.repository.full_name
        if (pull.number != payload.number
                or pull.base.repo.full_name.lower() != repository.lower()
                or str(pull.html_url).rstrip("/").lower() !=
                f"https://github.com/{repository}/pull/{payload.number}".lower()):
            raise WebhookError("Pull request does not match its repository", 422)
        if pull.state != "open" or pull.draft or pull.base.ref != "main":
            return 200, "Pull request is not ready for review"
        module = self._modules.find_by_repository_full_name(repository)
        if module is None or module.status != "completed" or not module.commit_sha:
            return 200, "Repository is not a published module"
        try:
            _, created = self._inbox.enqueue(
                delivery_id, module.id, repository, payload.installation.id, payload.number,
            )
        except ValueError as error:
            raise WebhookError(str(error), 409) from error
        return (202, "Review queued") if created else (200, "Delivery already received")
