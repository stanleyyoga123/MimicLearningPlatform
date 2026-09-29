from pathlib import Path

from apprenticeship.features.modules.module_record import ModuleRecord
from apprenticeship.features.modules.module_repository import ModuleRepository
from apprenticeship.features.submissions.submission_record import SubmissionRecord
from apprenticeship.features.submissions.submission_repository import SubmissionRepository
from apprenticeship.services.job_worker import JobWorker


class RecordingModulePipeline:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def run(self, module: ModuleRecord) -> None:
        self._events.append(f"module:{module.id}")


class RecordingSubmissionPipeline:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def run(self, submission: SubmissionRecord) -> None:
        self._events.append(f"submission:{submission.pr_number}")


class TimingOutSubmissionPipeline:
    def run(self, submission: SubmissionRecord) -> None:
        raise TimeoutError("Codex invocation timed out")


def test_worker_alternates_generation_and_review_when_both_queues_have_work(tmp_path: Path) -> None:
    database_path = tmp_path / "modules.sqlite3"
    modules = ModuleRepository(database_path)
    submissions = SubmissionRepository(database_path)
    modules.create("module-1")
    modules.create("module-2")
    for number in (1, 2):
        submissions.create_or_get(submissions.new(
            module_id=f"module-{number}",
            repository_full_name=f"owner/exercise-module-{number}",
            pr_number=number,
            pr_url=f"https://github.com/owner/exercise-module-{number}/pull/{number}",
            pr_title="Fix the exercise",
            base_sha="a" * 40,
            head_sha="b" * 40,
        ))
    events: list[str] = []
    worker = JobWorker(modules, RecordingModulePipeline(events), submissions, RecordingSubmissionPipeline(events))

    assert [worker.run_next() for _ in range(5)] == [True, True, True, True, False]
    assert events == ["module:module-1", "submission:1", "module:module-2", "submission:2"]


def test_review_timeout_becomes_retryable_worker_failure(tmp_path: Path) -> None:
    database_path = tmp_path / "modules.sqlite3"
    modules = ModuleRepository(database_path)
    submissions = SubmissionRepository(database_path)
    created = submissions.create_or_get(submissions.new(
        module_id="module-1", repository_full_name="owner/repo", pr_number=7,
        pr_url="https://github.com/owner/repo/pull/7", pr_title="Fix exercise",
        base_sha="a" * 40, head_sha="b" * 40,
    ))
    worker = JobWorker(modules, RecordingModulePipeline([]), submissions, TimingOutSubmissionPipeline())

    assert worker.run_next() is True
    failed = submissions.get(created.id)
    assert failed is not None and failed.status == "failed"
    assert failed.error == "Codex invocation timed out"
    queued = submissions.retry(created.id)
    assert queued is not None and queued.status == "queued"
