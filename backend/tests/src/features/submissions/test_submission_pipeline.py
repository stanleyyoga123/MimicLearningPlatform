from pathlib import Path

import pytest

from apprenticeship.features.modules.module_repository import ModuleRepository
from apprenticeship.features.submissions.submission_pipeline import SubmissionPipeline
from apprenticeship.features.submissions.submission_repository import SubmissionRepository
from tests.fixtures.submissions.published_module import reviewable_module
from tests.fixtures.submissions.github_review import github_pull
from tests.fixtures.submissions.review_pipeline import RecordingCodexReview, RecordingReviewPublisher


def _review_context(tmp_path: Path, response: dict):
    module_id = reviewable_module(tmp_path)
    database = tmp_path / "modules.sqlite3"
    repository = SubmissionRepository(database)
    record = repository.create_or_get(repository.new(
        module_id, "learner/webhook-module", 7,
        "https://github.com/learner/webhook-module/pull/7", "Prevent duplicate orders",
        "a" * 40, "b" * 40,
    ))
    codex = RecordingCodexReview(response)
    github = RecordingReviewPublisher()
    pipeline = SubmissionPipeline(repository, ModuleRepository(database), tmp_path, codex, github)
    return repository, record, codex, github, pipeline


@pytest.mark.parametrize(
    ("blocking", "status"),
    [(True, "needs_review"), (False, "success")],
)
def test_review_outcome_is_published_and_persisted_from_validated_findings(
    tmp_path: Path, blocking: bool, status: str,
) -> None:
    repository, record, codex, github, pipeline = _review_context(tmp_path, {
        "summary": "The change was reviewed against the exercise criteria.",
        "findings": [{"severity": "high" if blocking else "low", "blocking": blocking,
                      "body": "Repeated deliveries still create duplicate orders.",
                      "path": "app/orders.py", "line": 12, "side": "RIGHT"}],
    })

    result = pipeline.run(record)
    persisted = repository.get(record.id)

    assert result.status == status
    assert persisted is not None and persisted.status == status
    assert persisted.github_review_id == 74
    assert persisted.head_sha == "b" * 40
    assert len(codex.prompts) == 1
    assert "One order is created per delivery ID" in codex.prompts[0]
    assert "private-source-marker" not in codex.prompts[0]
    assert "private-reference-marker" not in codex.prompts[0]
    assert codex.workspaces[0].is_relative_to(tmp_path / "submissions")
    assert github.publish_calls == 1


def test_invalid_codex_result_cannot_publish_review(tmp_path: Path) -> None:
    repository, record, _codex, github, pipeline = _review_context(tmp_path, {
        "summary": "Looks fine.", "findings": [{"severity": "high", "blocking": True}],
    })

    with pytest.raises(RuntimeError, match="invalid review findings"):
        pipeline.run(record)

    stored = repository.get(record.id)
    assert stored is not None and stored.summary is None
    assert github.publish_calls == 0


def test_changed_head_before_publication_marks_review_outdated(tmp_path: Path) -> None:
    repository, record, _codex, github, pipeline = _review_context(tmp_path, {
        "summary": "The change meets the exercise criteria.", "findings": [],
    })
    github.pulls = [github_pull(), github_pull(head_sha="c" * 40)]

    result = pipeline.run(record)

    assert result.status == "outdated"
    assert repository.get(record.id).status == "outdated"
    assert github.publish_calls == 0


def test_retry_reconciles_review_after_ambiguous_publish_response(tmp_path: Path) -> None:
    repository, record, codex, github, pipeline = _review_context(tmp_path, {
        "summary": "The change meets the exercise criteria.", "findings": [],
    })
    github.fail_after_publish = True

    with pytest.raises(RuntimeError, match="Network failed"):
        pipeline.run(record)
    stored = repository.get(record.id)
    assert stored is not None and stored.summary == "The change meets the exercise criteria."
    stored.status = "failed"
    repository.save(stored)
    queued = repository.retry(record.id)
    assert queued is not None

    result = pipeline.run(queued)

    assert result.status == "success"
    assert result.github_review_id == 74
    assert github.publish_calls == 1
    assert len(codex.prompts) == 1
    assert github.snapshot_calls == 1


def test_unconfirmed_github_state_cannot_mark_submission_success(tmp_path: Path) -> None:
    repository, record, _codex, github, pipeline = _review_context(tmp_path, {
        "summary": "The change meets the exercise criteria.", "findings": [],
    })
    github.published_state = "PENDING"

    with pytest.raises(RuntimeError, match="state or commit"):
        pipeline.run(record)

    stored = repository.get(record.id)
    assert stored is not None and stored.status != "success"
