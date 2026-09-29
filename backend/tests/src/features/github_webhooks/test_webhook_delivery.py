"""Signed GitHub deliveries are persisted before local review work begins."""

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from apprenticeship.config.settings import Settings
from apprenticeship.features.github_webhooks.webhook_dispatcher import WebhookDispatcher
from apprenticeship.features.github_webhooks.webhook_inbox_repository import WebhookInboxRepository
from apprenticeship.features.modules.module_repository import ModuleRepository
from apprenticeship.features.submissions.submission_repository import SubmissionRepository
from apprenticeship.features.submissions.submission_service import SubmissionService
from apprenticeship.webhook_app import create_webhook_app
from tests.fixtures.submissions.github_review import RecordingGitHubReviewClient, github_pull
from tests.fixtures.submissions.published_module import reviewable_module


SECRET = "test-webhook-secret"


def _payload(*, action: str = "opened", repository: str = "learner/webhook-module") -> bytes:
    return json.dumps({
        "action": action,
        "number": 7,
        "repository": {"full_name": repository},
        "installation": {"id": 456},
        "pull_request": {
            "number": 7,
            "html_url": f"https://github.com/{repository}/pull/7",
            "state": "open",
            "draft": False,
            "base": {"ref": "main", "repo": {"full_name": repository}},
        },
    }).encode()


def _send(client: TestClient, raw: bytes, delivery: str = "delivery-1",
          event: str = "pull_request", secret: str = SECRET):
    signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return client.post("/webhooks/github", content=raw, headers={
        "X-Hub-Signature-256": f"sha256={signature}",
        "X-GitHub-Delivery": delivery,
        "X-GitHub-Event": event,
    })


def _review_dependencies(data_dir: Path, github: RecordingGitHubReviewClient):
    database = data_dir / "modules.sqlite3"
    modules = ModuleRepository(database)
    inbox = WebhookInboxRepository(database)
    submissions = SubmissionRepository(database)
    service = SubmissionService(submissions, modules, github)
    return modules, inbox, submissions, service


def test_signed_webhook_persists_once_without_starting_review(tmp_path: Path) -> None:
    module_id = reviewable_module(tmp_path)
    client = TestClient(create_webhook_app(Settings(
        data_dir=tmp_path, docker_image="test-image", github_webhook_secret=SECRET,
    )))
    raw = _payload()

    first = _send(client, raw)
    duplicate = _send(client, raw)
    inbox = WebhookInboxRepository(tmp_path / "modules.sqlite3")
    submissions = SubmissionRepository(tmp_path / "modules.sqlite3")

    assert first.status_code == 202
    assert duplicate.status_code == 200
    event = inbox.get("delivery-1")
    assert event is not None and event.module_id == module_id
    assert event.status == "queued"
    assert submissions.list_for_module(module_id) == []


def test_webhook_rejects_bad_signature_and_large_body_before_persistence(tmp_path: Path) -> None:
    reviewable_module(tmp_path)
    client = TestClient(create_webhook_app(Settings(
        data_dir=tmp_path, docker_image="test-image", github_webhook_secret=SECRET,
    )))

    forged = _send(client, _payload(), secret="wrong-secret")
    oversized = _send(client, b"x" * 2_000_001, delivery="delivery-2")

    assert forged.status_code == 401
    assert oversized.status_code == 413
    assert WebhookInboxRepository(tmp_path / "modules.sqlite3").list_recent() == []


def test_unknown_repository_and_irrelevant_action_are_ignored(tmp_path: Path) -> None:
    reviewable_module(tmp_path)
    client = TestClient(create_webhook_app(Settings(
        data_dir=tmp_path, docker_image="test-image", github_webhook_secret=SECRET,
    )))

    unknown = _send(client, _payload(repository="other/repository"))
    closed = _send(client, _payload(action="closed"), delivery="delivery-2")

    assert unknown.status_code == closed.status_code == 200
    assert WebhookInboxRepository(tmp_path / "modules.sqlite3").list_recent() == []


def test_public_webhook_app_exposes_only_signed_ingest(tmp_path: Path) -> None:
    module_id = reviewable_module(tmp_path)
    client = TestClient(create_webhook_app(Settings(
        data_dir=tmp_path, docker_image="test-image", github_webhook_secret=SECRET,
    )))

    assert _send(client, _payload()).status_code == 202
    assert client.get(f"/modules/{module_id}").status_code == 404
    assert client.get(f"/modules/{module_id}/submissions").status_code == 404
    assert client.get("/webhooks/github/deliveries").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.post("/webhooks/github", content=_payload()).status_code == 401


def test_dispatcher_uses_current_pr_revision_and_keeps_new_commit_during_active_review(
    tmp_path: Path, monkeypatch,
) -> None:
    import apprenticeship.features.github_webhooks.webhook_inbox_repository as inbox_module

    module_id = reviewable_module(tmp_path)
    github = RecordingGitHubReviewClient()
    modules, inbox, submissions, service = _review_dependencies(tmp_path, github)

    class App:
        def installation_id(self, repository: str) -> int:
            return 456

    now = datetime(2026, 9, 29, tzinfo=timezone.utc)
    monkeypatch.setattr(inbox_module, "_now", lambda: now)
    dispatcher = WebhookDispatcher(inbox, modules, service, App())
    inbox.enqueue("older-delivery", module_id, "learner/webhook-module", 456, 7)
    assert dispatcher.process_next()
    first = submissions.list_for_module(module_id)[0]
    assert first.head_sha == "b" * 40

    github.pull = github_pull(head_sha="c" * 40)
    inbox.enqueue("newer-delivery", module_id, "learner/webhook-module", 456, 7)
    assert dispatcher.process_next()
    pending = inbox.get("newer-delivery")
    assert pending is not None and pending.status == "queued"
    assert len(submissions.list_for_module(module_id)) == 1

    first.status = "needs_review"
    first.stage = "completed"
    submissions.save(first)
    now += timedelta(seconds=11)
    assert dispatcher.process_next()
    latest = submissions.list_for_module(module_id)[0]
    assert latest.head_sha == "c" * 40
    assert len(submissions.list_for_module(module_id)) == 2


def test_installation_mismatch_never_queues_a_submission(tmp_path: Path) -> None:
    module_id = reviewable_module(tmp_path)
    github = RecordingGitHubReviewClient()
    modules, inbox, submissions, service = _review_dependencies(tmp_path, github)

    class OtherApp:
        def installation_id(self, repository: str) -> int:
            return 999

    inbox.enqueue("mismatched-installation", module_id, "learner/webhook-module", 456, 7)
    dispatcher = WebhookDispatcher(inbox, modules, service, OtherApp())

    assert dispatcher.process_next()
    result = inbox.get("mismatched-installation")
    assert result is not None and result.status == "failed"
    assert submissions.list_for_module(module_id) == []


def test_transient_installation_failure_retries_same_delivery(
    tmp_path: Path, monkeypatch,
) -> None:
    import apprenticeship.features.github_webhooks.webhook_inbox_repository as inbox_module

    module_id = reviewable_module(tmp_path)
    github = RecordingGitHubReviewClient()
    modules, inbox, submissions, service = _review_dependencies(tmp_path, github)
    now = datetime(2026, 9, 29, tzinfo=timezone.utc)
    monkeypatch.setattr(inbox_module, "_now", lambda: now)

    class FlakyApp:
        calls = 0

        def installation_id(self, repository: str) -> int:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("GitHub App request timed out; retry this submission")
            return 456

    app = FlakyApp()
    dispatcher = WebhookDispatcher(inbox, modules, service, app)
    inbox.enqueue("transient", module_id, "learner/webhook-module", 456, 7)

    assert dispatcher.process_next()
    delayed = inbox.get("transient")
    assert delayed is not None and delayed.status == "queued"
    assert delayed.attempts == 1
    assert submissions.list_for_module(module_id) == []

    now += timedelta(seconds=3)
    assert dispatcher.process_next()
    completed = inbox.get("transient")
    assert completed is not None and completed.status == "completed"
    assert app.calls == 2
    assert len(submissions.list_for_module(module_id)) == 1


def test_interrupted_delivery_is_replayed_after_restart(tmp_path: Path) -> None:
    module_id = reviewable_module(tmp_path)
    database = tmp_path / "modules.sqlite3"
    inbox = WebhookInboxRepository(database)
    inbox.enqueue("interrupted", module_id, "learner/webhook-module", 456, 7)
    assert inbox.claim_next().status == "running"

    restarted = WebhookInboxRepository(database)
    restarted.recover_interrupted()
    claimed = restarted.claim_next()

    assert claimed is not None and claimed.delivery_id == "interrupted"
    assert claimed.status == "running"
