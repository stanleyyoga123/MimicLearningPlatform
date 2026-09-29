from pathlib import Path

import pytest

from apprenticeship.features.submissions.submission_record import SubmissionRecord
from apprenticeship.features.submissions.submission_repository import SubmissionRepository


def _new_submission(repository: SubmissionRepository, head_sha: str = "b" * 40) -> SubmissionRecord:
    return repository.new(
        module_id="module-1",
        repository_full_name="owner/exercise-module-1",
        pr_number=12,
        pr_url="https://github.com/owner/exercise-module-1/pull/12",
        pr_title="Fix duplicate orders",
        base_sha="a" * 40,
        head_sha=head_sha,
    )


def test_same_pr_revision_is_reused_after_completion_and_survives_restart(tmp_path: Path) -> None:
    repository = SubmissionRepository(tmp_path / "modules.sqlite3")
    first = repository.create_or_get(_new_submission(repository))
    first.status = "success"
    first.stage = "completed"
    first.github_review_id = 42
    repository.save(first)

    restarted = SubmissionRepository(tmp_path / "modules.sqlite3")
    duplicate = restarted.create_or_get(_new_submission(restarted))

    assert duplicate.id == first.id
    assert duplicate.github_review_id == 42
    assert len(restarted.list_for_module("module-1")) == 1


def test_new_revision_waits_while_same_pr_review_is_active(tmp_path: Path) -> None:
    repository = SubmissionRepository(tmp_path / "modules.sqlite3")
    first = repository.create_or_get(_new_submission(repository))

    with pytest.raises(ValueError, match="already in progress"):
        repository.create_or_get(_new_submission(repository, head_sha="c" * 40))

    first.status = "needs_review"
    first.stage = "completed"
    repository.save(first)
    second = repository.create_or_get(_new_submission(repository, head_sha="c" * 40))

    assert second.id != first.id
    assert second.status == "queued"
    assert len(repository.list_for_module("module-1")) == 2


def test_interrupted_review_can_be_retried_without_losing_saved_findings(tmp_path: Path) -> None:
    database_path = tmp_path / "modules.sqlite3"
    repository = SubmissionRepository(database_path)
    created = repository.create_or_get(_new_submission(repository))
    claimed = repository.claim_next()
    assert claimed is not None and claimed.id == created.id
    claimed.stage = "publishing"
    claimed.summary = "One blocking problem was found."
    repository.save(claimed)

    restarted = SubmissionRepository(database_path)
    restarted.fail_interrupted()
    failed = restarted.get(created.id)
    assert failed is not None and failed.status == "failed"
    assert failed.stage == "publishing"
    assert failed.error is not None and "Retry" in failed.error

    queued = restarted.retry(created.id)
    assert queued is not None and queued.status == "queued"
    assert queued.summary == "One blocking problem was found."
