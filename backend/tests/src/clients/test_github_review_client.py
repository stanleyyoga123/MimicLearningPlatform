import io
import json
import subprocess
import urllib.request
from pathlib import Path

import pytest

from apprenticeship.clients.github_review_client import GitHubReviewClient
from apprenticeship.features.submissions.submission_record import ReviewFinding


class FakeGitHubApp:
    def __init__(self) -> None:
        self.repositories: list[str] = []

    def token_for(self, repository: str) -> str:
        self.repositories.append(repository)
        return "test-installation-token"

    def reviewer_login(self) -> str:
        return "reviewer[bot]"


@pytest.mark.parametrize(
    ("blocking", "event"),
    [(True, "REQUEST_CHANGES"), (False, "APPROVE")],
)
def test_publish_review_uses_blocking_outcome_and_only_valid_inline_positions(
    monkeypatch: pytest.MonkeyPatch, blocking: bool, event: str,
) -> None:
    sent: list[urllib.request.Request] = []

    def fake_urlopen(request: urllib.request.Request, timeout: int) -> io.BytesIO:
        sent.append(request)
        return io.BytesIO(json.dumps({
            "id": 74,
            "html_url": "https://github.com/owner/repo/pull/7#pullrequestreview-74",
            "commit_id": "b" * 40,
            "state": "CHANGES_REQUESTED" if blocking else "APPROVED",
            "user": {"login": "reviewer"},
        }).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    findings = [
        ReviewFinding(severity="high", blocking=blocking, body="Duplicate deliveries still create a second order.",
                      path="app/orders.py", line=12, side="RIGHT"),
        ReviewFinding(severity="low", blocking=False, body="Consider a clearer variable name in this handler.",
                      path="app/orders.py", line=30, side="RIGHT"),
    ]

    app = FakeGitHubApp()
    result = GitHubReviewClient(app).publish_review(
        "owner/repo", 7, "b" * 40, "<!-- submission:123 -->", "Review complete.",
        findings, frozenset({("app/orders.py", 12, "RIGHT")}),
    )

    payload = json.loads(sent[0].data or b"{}")
    assert result.id == 74
    assert payload["event"] == event
    assert payload["commit_id"] == "b" * 40
    assert payload["comments"] == [{
        "path": "app/orders.py", "line": 12, "side": "RIGHT",
        "body": "Duplicate deliveries still create a second order.",
    }]
    assert "Consider a clearer variable name" in payload["body"]
    assert "<!-- submission:123 -->" in payload["body"]
    assert sent[0].get_header("Authorization") == "Bearer test-installation-token"
    assert app.repositories == ["owner/repo"]


def test_find_review_reconciles_existing_marker_on_same_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_urlopen(request: urllib.request.Request, timeout: int) -> io.BytesIO:
        calls.append(request.full_url)
        return io.BytesIO(json.dumps([
            {"id": 1, "html_url": "https://github.com/owner/repo/pull/7#pullrequestreview-1",
             "commit_id": "a" * 40, "body": "<!-- submission:123 -->",
             "state": "APPROVED", "user": {"login": "reviewer[bot]"}},
            {"id": 2, "html_url": "https://github.com/owner/repo/pull/7#pullrequestreview-2",
             "commit_id": "b" * 40, "body": "Review complete. <!-- submission:123 -->",
             "state": "APPROVED", "user": {"login": "reviewer[bot]"}},
        ]).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    review = GitHubReviewClient(FakeGitHubApp()).find_review(
        "owner/repo", 7, "<!-- submission:123 -->", "b" * 40,
    )

    assert review is not None and review.id == 2
    assert calls == [
        "https://api.github.com/repos/owner/repo/pulls/7/reviews?per_page=100&page=1",
    ]


def test_snapshot_reviews_merge_base_change_and_tracks_deleted_file_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_sha, head_sha, merge_sha, starter_sha = (letter * 40 for letter in "abcd")
    diff = (
        "diff --git a/app/removed.py b/app/removed.py\n"
        "--- a/app/removed.py\n+++ /dev/null\n"
        "@@ -3 +0,0 @@\n-old behavior\n"
        "diff --git a/app/new.py b/app/new.py\n"
        "--- /dev/null\n+++ b/app/new.py\n"
        "@@ -0,0 +1 @@\n+new behavior\n"
    )
    commands: list[tuple[str, ...]] = []

    def fake_git_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        args = tuple(command[5:] if command[3] == "-c" else command[3:])
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        assert "GITHUB_APP_PRIVATE_KEY_PATH" not in environment
        assert "GITHUB_WEBHOOK_SECRET" not in environment
        if args[0] == "fetch":
            assert environment["APPRENTICESHIP_INSTALLATION_TOKEN"] == "test-installation-token"
        else:
            assert "APPRENTICESHIP_INSTALLATION_TOKEN" not in environment
        commands.append(args)
        output = ""
        if args == ("merge-base", base_sha, head_sha):
            output = merge_sha + "\n"
        elif args[:3] == ("diff", "--name-only", "-z"):
            output = "app/removed.py\0app/new.py\0"
        elif args[:3] == ("diff", "--no-ext-diff", "--unified=3"):
            output = diff
        elif args[:3] == ("diff", "--no-ext-diff", "--unified=0"):
            output = diff
        return subprocess.CompletedProcess(command, 0, output)

    monkeypatch.setattr(subprocess, "run", fake_git_run)

    snapshot = GitHubReviewClient(FakeGitHubApp()).fetch_snapshot(
        "owner/repo", 7, base_sha, head_sha, starter_sha, tmp_path / "snapshot",
    )

    assert snapshot.diff == diff
    assert ("app/removed.py", 3, "LEFT") in snapshot.changed_lines
    assert ("app/new.py", 1, "RIGHT") in snapshot.changed_lines
    assert ("diff", "--no-ext-diff", "--unified=3", merge_sha, head_sha) in commands
    assert ("diff", "--no-ext-diff", "--unified=3", base_sha, head_sha) not in commands


@pytest.mark.parametrize(
    ("special_tree", "mode"),
    [("head", "120000"), ("starter", "160000"), ("merge_base", "120000")],
)
def test_snapshot_rejects_symlinks_and_submodules_in_required_source_trees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, special_tree: str, mode: str,
) -> None:
    base_sha, head_sha, merge_sha, starter_sha = (letter * 40 for letter in "abcd")
    selected = {"head": head_sha, "starter": starter_sha, "merge_base": merge_sha}[special_tree]

    def fake_git_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        args = tuple(command[5:] if command[3] == "-c" else command[3:])
        output = ""
        if args == ("merge-base", base_sha, head_sha):
            output = merge_sha + "\n"
        elif args[:3] == ("diff", "--name-only", "-z"):
            output = "app/orders.py\0"
        elif args[:3] == ("ls-tree", "-r", "-z") and args[3] == selected:
            output = f"{mode} blob {'e' * 40}\tapp/orders.py\0"
        return subprocess.CompletedProcess(command, 0, output)

    monkeypatch.setattr(subprocess, "run", fake_git_run)

    with pytest.raises(ValueError, match="symlinks or submodules"):
        GitHubReviewClient(FakeGitHubApp()).fetch_snapshot(
            "owner/repo", 7, base_sha, head_sha, starter_sha, tmp_path / "snapshot",
        )
