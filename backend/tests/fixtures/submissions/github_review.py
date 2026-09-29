from apprenticeship.clients.github_review_models import GitHubPull


def github_pull(
    *, number: int = 7, state: str = "open", draft: bool = False,
    base_ref: str = "main", author: str = "junior", base_sha: str = "a" * 40,
    head_sha: str = "b" * 40,
) -> GitHubPull:
    return GitHubPull.model_validate({
        "number": number,
        "title": "Prevent duplicate orders",
        "html_url": f"https://github.com/learner/webhook-module/pull/{number}",
        "state": state,
        "draft": draft,
        "base": {"sha": base_sha, "ref": base_ref},
        "head": {"sha": head_sha, "ref": "fix-orders"},
        "user": {"login": author},
    })


class RecordingGitHubReviewClient:
    def __init__(self, pull: GitHubPull | None = None, reviewer: str = "reviewer") -> None:
        self.pull = pull or github_pull()
        self.reviewer = reviewer
        self.get_calls: list[tuple[str, int]] = []

    def get_pull(self, repository: str, number: int) -> GitHubPull:
        self.get_calls.append((repository, number))
        return self.pull

    def reviewer_login(self) -> str:
        return self.reviewer
