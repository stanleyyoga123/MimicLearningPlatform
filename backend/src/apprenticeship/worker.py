import os
import time
import fcntl
from pathlib import Path

from apprenticeship.clients.codex_client import CodexClient
from apprenticeship.clients.github_publisher import GitHubPublisher
from apprenticeship.clients.github_review_client import GitHubReviewClient
from apprenticeship.clients.github_app_client import GitHubAppClient
from apprenticeship.config.settings import Settings
from apprenticeship.features.modules.module_pipeline import ModulePipeline
from apprenticeship.features.modules.module_repository import ModuleRepository
from apprenticeship.features.submissions.submission_pipeline import SubmissionPipeline
from apprenticeship.features.submissions.submission_repository import SubmissionRepository
from apprenticeship.features.submissions.submission_service import SubmissionService
from apprenticeship.features.github_webhooks.webhook_dispatcher import WebhookDispatcher
from apprenticeship.features.github_webhooks.webhook_inbox_repository import WebhookInboxRepository
from apprenticeship.features.verification.docker_verifier import DockerVerifier
from apprenticeship.services.job_worker import JobWorker


def run_worker(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    with (settings.data_dir / "worker.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another generation/review worker is already running") from error
        _run_locked_worker(settings)


def _run_locked_worker(settings: Settings) -> None:
    repository = ModuleRepository(settings.data_dir / "modules.sqlite3")
    submissions = SubmissionRepository(settings.data_dir / "modules.sqlite3")
    repository.fail_interrupted()
    submissions.fail_interrupted()
    publisher = GitHubPublisher(settings.github_token) if settings.github_token else None
    github_app = (
        GitHubAppClient(settings.github_app_id, settings.github_app_private_key_path)
        if settings.github_app_id and settings.github_app_private_key_path else None
    )
    reviewer = GitHubReviewClient(github_app) if github_app else None
    inbox = WebhookInboxRepository(settings.data_dir / "modules.sqlite3")
    dispatcher = WebhookDispatcher(
        inbox, repository, SubmissionService(submissions, repository, reviewer), github_app,
    )
    dispatcher.recover_interrupted()
    for name in ("GITHUB_TOKEN", "GITHUB_REVIEW_TOKEN", "GH_TOKEN", "GH_ENTERPRISE_TOKEN",
                 "OPENROUTER_API_KEY", "GITHUB_APP_PRIVATE_KEY_PATH", "GITHUB_WEBHOOK_SECRET"):
        os.environ.pop(name, None)
    codex = CodexClient(settings.codex_binary, settings.codex_model)
    pipeline = ModulePipeline(
        repository=repository,
        data_dir=settings.data_dir,
        scaffold_dir=Path(__file__).resolve().parents[2] / "scaffold",
        codex=codex,
        verifier=DockerVerifier(settings.docker_image),
        publisher=publisher,
    )
    submission_pipeline = SubmissionPipeline(
        repository=submissions, modules=repository, data_dir=settings.data_dir,
        codex=codex, github=reviewer,
    )
    worker = JobWorker(repository, pipeline, submissions, submission_pipeline)
    while True:
        dispatched = dispatcher.process_next()
        if not worker.run_next() and not dispatched:
            time.sleep(1)


if __name__ == "__main__":
    run_worker(Settings.from_environment())
