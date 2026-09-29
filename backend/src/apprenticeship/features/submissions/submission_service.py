import re
from urllib.parse import urlparse

from apprenticeship.clients.github_review_client import GitHubReviewClient
from apprenticeship.clients.github_review_models import GitHubPull
from apprenticeship.features.modules.module_repository import ModuleRepository
from apprenticeship.features.submissions.submission_record import SubmissionRecord
from apprenticeship.features.submissions.submission_repository import SubmissionRepository


class SubmissionError(ValueError):
    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


class SubmissionService:
    def __init__(self, repository: SubmissionRepository, modules: ModuleRepository,
                 github: GitHubReviewClient | None):
        self._repository = repository
        self._modules = modules
        self._github = github

    def submit(self, module_id: str, pr_url: str) -> SubmissionRecord:
        module = self._modules.get(module_id)
        if module is None:
            raise SubmissionError("Module not found", 404)
        if module.status != "completed" or not module.repository_url or not module.commit_sha:
            raise SubmissionError("The module must be published before submissions can be reviewed")
        if self._github is None:
            raise SubmissionError("GitHub App is not configured for reviews", 503)
        repository = self._modules.repository_full_name(module_id)
        if not repository:
            raise SubmissionError("Published repository details are unavailable")
        number = self._parse_pr_url(pr_url, repository)
        try:
            pull = self._github.get_pull(repository, number)
            reviewer = self._github.reviewer_login()
        except RuntimeError as error:
            raise SubmissionError(str(error), 502) from error
        self._validate_pull(pull, repository, number, reviewer)
        record = SubmissionRepository.new(
            module_id, repository, number, str(pull.html_url), pull.title,
            pull.base.sha, pull.head.sha,
        )
        try:
            return self._repository.create_or_get(record)
        except ValueError as error:
            raise SubmissionError(str(error)) from error

    def list(self, module_id: str) -> list[SubmissionRecord]:
        if self._modules.get(module_id) is None:
            raise SubmissionError("Module not found", 404)
        return self._repository.list_for_module(module_id)

    def get(self, submission_id: str) -> SubmissionRecord:
        record = self._repository.get(submission_id)
        if record is None:
            raise SubmissionError("Submission not found", 404)
        return record

    def retry(self, submission_id: str) -> SubmissionRecord:
        record = self.get(submission_id)
        if record.status != "failed":
            raise SubmissionError("Only failed reviews can be retried")
        if self._github is None:
            raise SubmissionError("GitHub App is not configured for reviews", 503)
        try:
            pull = self._github.get_pull(record.repository_full_name, record.pr_number)
            reviewer = self._github.reviewer_login()
        except RuntimeError as error:
            raise SubmissionError(str(error), 502) from error
        self._validate_pull(pull, record.repository_full_name, record.pr_number, reviewer)
        if pull.base.sha != record.base_sha or pull.head.sha != record.head_sha:
            record.status = "outdated"
            record.error = "The pull request changed. Submit its latest revision for review."
            self._repository.save(record)
            raise SubmissionError(record.error)
        try:
            result = self._repository.retry(submission_id)
        except ValueError as error:
            raise SubmissionError(str(error)) from error
        if result is None:
            raise SubmissionError("Submission not found", 404)
        return result

    @staticmethod
    def _parse_pr_url(pr_url: str, repository: str) -> int:
        url = urlparse(pr_url)
        if (url.scheme != "https" or url.netloc != "github.com"
                or url.query or url.fragment):
            raise SubmissionError("Enter an HTTPS GitHub pull request URL", 422)
        match = re.fullmatch(r"/([^/]+)/([^/]+)/pull/(\d+)/?", url.path)
        if not match or f"{match.group(1)}/{match.group(2)}".lower() != repository.lower():
            raise SubmissionError("Pull request URL must belong to this module's repository", 422)
        return int(match.group(3))

    @staticmethod
    def _validate_pull(pull: GitHubPull, repository: str, number: int,
                       reviewer: str) -> None:
        if pull.number != number or str(pull.html_url).rstrip("/").lower() != (
            f"https://github.com/{repository}/pull/{number}".lower()
        ):
            raise SubmissionError("GitHub pull request does not match the submitted URL")
        if pull.state != "open" or pull.draft:
            raise SubmissionError("Pull request must be open and ready for review")
        if pull.base.ref != "main":
            raise SubmissionError("Pull request must target the module's main branch")
        if pull.user.login.lower() == reviewer.lower():
            raise SubmissionError("Reviewer account cannot review its own pull request")
