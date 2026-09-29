import logging
from typing import Protocol

from apprenticeship.features.github_webhooks.webhook_event import WebhookEvent
from apprenticeship.features.github_webhooks.webhook_inbox_repository import WebhookInboxRepository
from apprenticeship.features.modules.module_repository import ModuleRepository
from apprenticeship.features.submissions.submission_service import SubmissionError, SubmissionService


class GitHubInstallationLookup(Protocol):
    def installation_id(self, repository: str) -> int: ...


class WebhookDispatcher:
    def __init__(self, inbox: WebhookInboxRepository, modules: ModuleRepository,
                 submissions: SubmissionService, github_app: GitHubInstallationLookup | None):
        self._inbox = inbox
        self._modules = modules
        self._submissions = submissions
        self._github_app = github_app

    def recover_interrupted(self) -> None:
        self._inbox.recover_interrupted()

    def process_next(self) -> bool:
        event = self._inbox.claim_next()
        if event is None:
            return False
        try:
            self._dispatch(event)
        except Exception as error:
            logging.error("Unexpected webhook dispatch failure for delivery %s (%s)",
                          event.delivery_id, type(error).__name__)
            self._inbox.fail(event, "Webhook dispatch failed unexpectedly; retry this delivery",
                             retryable=False)
        return True

    def _dispatch(self, event: WebhookEvent) -> None:
        module = self._modules.get(event.module_id)
        repository = self._modules.repository_full_name(event.module_id)
        if (module is None or module.status != "completed" or repository is None
                or repository.lower() != event.repository_full_name.lower()):
            self._inbox.complete(event, ignored=True, reason="Module is no longer published")
            return
        if self._github_app is None:
            self._inbox.fail(event, "GitHub App is not configured", retryable=True)
            return
        try:
            installation_id = self._github_app.installation_id(event.repository_full_name)
        except RuntimeError as error:
            self._inbox.fail(event, str(error), retryable=True)
            return
        if installation_id != event.installation_id:
            self._inbox.fail(event, "Webhook installation does not match the configured GitHub App",
                             retryable=False)
            return
        url = f"https://github.com/{event.repository_full_name}/pull/{event.pr_number}"
        try:
            submission = self._submissions.submit(event.module_id, url)
            if submission.status == "failed":
                self._submissions.retry(submission.id)
            elif submission.status == "outdated":
                self._inbox.fail(event, "Current pull request revision is outdated", retryable=False)
                return
        except SubmissionError as error:
            if error.status_code == 409 and "already in progress" in str(error):
                self._inbox.postpone(event)
            elif error.status_code == 409 and "open and ready" in str(error):
                self._inbox.complete(event, ignored=True, reason=str(error))
            elif error.status_code == 502 and "(HTTP 404)" in str(error):
                self._inbox.complete(event, ignored=True, reason="Pull request is unavailable")
            elif error.status_code >= 500:
                self._inbox.fail(event, str(error), retryable=True)
            else:
                self._inbox.fail(event, str(error), retryable=False)
            return
        self._inbox.complete(event)
