import io
import json
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apprenticeship.config.settings import Settings
from apprenticeship.clients.github_review_client import GitHubReviewClient
from apprenticeship.features.submissions.submission_repository import SubmissionRepository
from apprenticeship.main import create_app
from tests.fixtures.submissions.github_review import RecordingGitHubReviewClient, github_pull
from tests.fixtures.submissions.published_module import reviewable_module


def _client(data_dir: Path, github: RecordingGitHubReviewClient | None) -> TestClient:
    return TestClient(create_app(Settings(data_dir=data_dir, docker_image="test-image"), review_client=github))


def test_submission_routes_persist_review_and_reuse_same_revision(tmp_path: Path) -> None:
    module_id = reviewable_module(tmp_path)
    github = RecordingGitHubReviewClient()
    client = _client(tmp_path, github)
    path = f"/modules/{module_id}/submissions"
    request = {"pr_url": "https://github.com/learner/webhook-module/pull/7"}

    created = client.post(path, json=request)
    duplicate = client.post(path, json=request)
    history = _client(tmp_path, github).get(path)
    detail = _client(tmp_path, github).get(f"/submissions/{created.json()['id']}")

    assert created.status_code == duplicate.status_code == 202
    assert created.json()["id"] == duplicate.json()["id"]
    assert created.json()["status"] == "queued"
    assert created.json()["base_sha"] == "a" * 40
    assert created.json()["head_sha"] == "b" * 40
    assert history.status_code == detail.status_code == 200
    assert [item["id"] for item in history.json()] == [created.json()["id"]]
    assert detail.json()["pr_title"] == "Prevent duplicate orders"
    assert github.get_calls == [("learner/webhook-module", 7)] * 2


@pytest.mark.parametrize(
    ("pull", "detail"),
    [
        (github_pull(state="closed"), "open"),
        (github_pull(draft=True), "ready"),
        (github_pull(base_ref="develop"), "main"),
        (github_pull(author="reviewer"), "own pull request"),
    ],
)
def test_submission_rejects_pr_that_cannot_be_reviewed(
    tmp_path: Path, pull, detail: str,
) -> None:
    module_id = reviewable_module(tmp_path)
    client = _client(tmp_path, RecordingGitHubReviewClient(pull))

    response = client.post(
        f"/modules/{module_id}/submissions",
        json={"pr_url": "https://github.com/learner/webhook-module/pull/7"},
    )

    assert response.status_code == 409
    assert detail in response.json()["detail"]
    assert client.get(f"/modules/{module_id}/submissions").json() == []


def test_submission_rejects_foreign_pr_url_without_calling_github(tmp_path: Path) -> None:
    module_id = reviewable_module(tmp_path)
    github = RecordingGitHubReviewClient()
    client = _client(tmp_path, github)

    response = client.post(
        f"/modules/{module_id}/submissions",
        json={"pr_url": "https://github.com/other/repository/pull/7"},
    )

    assert response.status_code == 422
    assert github.get_calls == []


def test_retry_rejects_changed_revision_and_records_outdated_status(tmp_path: Path) -> None:
    module_id = reviewable_module(tmp_path)
    github = RecordingGitHubReviewClient()
    client = _client(tmp_path, github)
    created = client.post(
        f"/modules/{module_id}/submissions",
        json={"pr_url": "https://github.com/learner/webhook-module/pull/7"},
    ).json()
    repository = SubmissionRepository(tmp_path / "modules.sqlite3")
    record = repository.get(created["id"])
    assert record is not None
    record.status = "failed"
    repository.save(record)
    github.pull = github_pull(head_sha="c" * 40)

    retry = client.post(f"/submissions/{record.id}/retry")
    result = client.get(f"/submissions/{record.id}")

    assert retry.status_code == 409
    assert "changed" in retry.json()["detail"]
    assert result.json()["status"] == "outdated"


def test_reopened_pr_requeues_outdated_same_revision_after_live_validation(tmp_path: Path) -> None:
    module_id = reviewable_module(tmp_path)
    github = RecordingGitHubReviewClient()
    client = _client(tmp_path, github)
    path = f"/modules/{module_id}/submissions"
    request = {"pr_url": "https://github.com/learner/webhook-module/pull/7"}
    created = client.post(path, json=request).json()
    repository = SubmissionRepository(tmp_path / "modules.sqlite3")
    record = repository.get(created["id"])
    assert record is not None
    record.status = "outdated"
    record.error = "The pull request changed"
    repository.save(record)

    github.pull = github_pull(state="closed")
    closed = client.post(path, json=request)
    assert closed.status_code == 409
    assert repository.get(record.id).status == "outdated"

    github.pull = github_pull()
    reopened = client.post(path, json=request)
    assert reopened.status_code == 202
    assert reopened.json()["id"] == record.id
    assert reopened.json()["status"] == "queued"
    assert len(repository.list_for_module(module_id)) == 1


@pytest.mark.parametrize("failure", ["identity", "json", "timeout"])
def test_github_reviewer_failures_return_actionable_502_without_queuing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    module_id = reviewable_module(tmp_path)
    pull_payload = github_pull().model_dump(mode="json")

    class FakeApp:
        def token_for(self, repository: str) -> str:
            return "test-installation-token"

        def reviewer_login(self) -> str:
            if failure == "identity":
                raise RuntimeError("GitHub returned incomplete App details")
            return "reviewer[bot]"

    def fake_urlopen(request: urllib.request.Request, timeout: int) -> io.BytesIO:
        if request.full_url.endswith("/pulls/7"):
            if failure == "json":
                return io.BytesIO(b"{incomplete")
            if failure == "timeout":
                raise TimeoutError("private upstream timeout details")
            return io.BytesIO(json.dumps(pull_payload).encode("utf-8"))
        raise AssertionError(f"Unexpected GitHub endpoint: {request.full_url}")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = TestClient(create_app(
        Settings(data_dir=tmp_path, docker_image="test-image"),
        review_client=GitHubReviewClient(FakeApp()),
    ))

    response = client.post(
        f"/modules/{module_id}/submissions",
        json={"pr_url": "https://github.com/learner/webhook-module/pull/7"},
    )

    assert response.status_code == 502
    assert "GitHub" in response.json()["detail"]
    assert "test-installation-token" not in response.text
    assert "private upstream timeout details" not in response.text
    assert client.get(f"/modules/{module_id}/submissions").json() == []
