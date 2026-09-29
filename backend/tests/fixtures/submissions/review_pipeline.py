from pathlib import Path

from apprenticeship.clients.github_review_models import GitHubPull, PublishedReview, ReviewSnapshot
from apprenticeship.features.submissions.submission_record import ReviewFinding
from tests.fixtures.submissions.github_review import github_pull


class RecordingCodexReview:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.prompts: list[str] = []
        self.workspaces: list[Path] = []

    def review(self, prompt: str, workspace: Path, output_schema: dict, output_path: Path) -> dict:
        self.prompts.append(prompt)
        self.workspaces.append(workspace)
        return self.response


class RecordingReviewPublisher:
    def __init__(self) -> None:
        self.pulls: list[GitHubPull] = [github_pull()]
        self.published: PublishedReview | None = None
        self.publish_calls = 0
        self.snapshot_calls = 0
        self.fail_after_publish = False
        self.published_state: str | None = None

    def get_pull(self, repository: str, number: int) -> GitHubPull:
        return self.pulls.pop(0) if len(self.pulls) > 1 else self.pulls[0]

    def reviewer_login(self) -> str:
        return "reviewer"

    def fetch_snapshot(self, repository: str, number: int, base_sha: str,
                       head_sha: str, starter_sha: str, workspace: Path) -> ReviewSnapshot:
        self.snapshot_calls += 1
        workspace.mkdir(parents=True)
        (workspace / "review_material.txt").write_text("<file path=\"app/orders.py\">\n# learner changes\n</file>\n")
        (workspace / "starter_material.txt").write_text("<file path=\"app/orders.py\">\n# starter\n</file>\n")
        return ReviewSnapshot(
            workspace, "diff --git a/app/orders.py b/app/orders.py\n+new code\n",
            frozenset({("app/orders.py", 12, "RIGHT")}), frozenset({"app/orders.py"}),
        )

    def find_review(self, repository: str, number: int, marker: str,
                    head_sha: str) -> PublishedReview | None:
        return self.published if self.published and marker in (self.published.body or "") else None

    def publish_review(self, repository: str, number: int, head_sha: str, marker: str,
                       summary: str, findings: list[ReviewFinding],
                       changed_lines: frozenset[tuple[str, int, str]]) -> PublishedReview:
        self.publish_calls += 1
        state = self.published_state or (
            "CHANGES_REQUESTED" if any(finding.blocking for finding in findings) else "APPROVED"
        )
        self.published = PublishedReview.model_validate({
            "id": 74,
            "html_url": f"https://github.com/{repository}/pull/{number}#pullrequestreview-74",
            "body": summary + " " + marker,
            "commit_id": head_sha,
            "user": {"login": "reviewer"},
            "state": state,
        })
        if self.fail_after_publish:
            self.fail_after_publish = False
            raise RuntimeError("Network failed after GitHub accepted the review")
        return self.published
