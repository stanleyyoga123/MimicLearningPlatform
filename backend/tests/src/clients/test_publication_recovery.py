"""Publication integration against a real local Git remote and fake GitHub API."""

import io
import json
import subprocess
import urllib.error
from pathlib import Path

import pytest

from apprenticeship.clients.github_publisher import GitHubPublisher


def git(directory: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=directory, text=True, capture_output=True, check=True,
    )
    return result.stdout.strip()


class LocalGitHubPublisher(GitHubPublisher):
    """Use real Git operations with only the remote HTTP boundary replaced."""

    def __init__(self, remote: Path) -> None:
        super().__init__("local-test-token")
        self.remote = remote
        self.repository: dict | None = None
        self.creations = 0
        self.fail_after_push = False
        self.create_conflict_after_creation = False
        self.missing_ref_status = 404
        self.missing_ref_body: dict[str, object] = {"message": "Git Repository is empty."}
        self.pushes = 0

    def _request(self, method: str, path: str, data: dict | None = None) -> dict:
        if method == "GET" and path == "/user":
            return {"login": "learner"}
        if method == "POST" and path == "/user/repos":
            assert data is not None and data["private"] is True
            self.creations += 1
            self.repository = {
                "full_name": f"learner/{data['name']}", "html_url": f"https://github.com/learner/{data['name']}",
                "private": True, "description": data["description"],
            }
            if self.create_conflict_after_creation:
                raise urllib.error.HTTPError(path, 422, "Repository already exists", {}, None)
            return self.repository
        if method == "GET" and path.endswith("/git/ref/heads/main"):
            result = subprocess.run(
                ["git", "--git-dir", str(self.remote), "rev-parse", "--verify", "refs/heads/main"],
                text=True, capture_output=True,
            )
            if result.returncode:
                body = io.BytesIO(json.dumps(self.missing_ref_body).encode("utf-8"))
                raise urllib.error.HTTPError(path, self.missing_ref_status, "Missing branch", {}, body)
            return {"object": {"sha": result.stdout.strip()}}
        if method == "GET" and "/git/commits/" in path:
            sha = path.rsplit("/", 1)[-1]
            return {
                "tree": {"sha": git(self.remote, "rev-parse", f"{sha}^{{tree}}")},
                "message": git(self.remote, "show", "-s", "--format=%B", sha),
            }
        if method == "GET" and path.startswith("/repos/"):
            if self.repository is None:
                raise urllib.error.HTTPError(path, 404, "Missing repository", {}, None)
            return self.repository
        raise AssertionError(f"Unexpected GitHub request: {method} {path}")

    def _git(self, directory: Path, *args: str, env: dict[str, str] | None = None) -> str:
        if "push" in args:
            self.pushes += 1
            arguments = list(args)
            index = arguments.index("push")
            arguments[index + 1] = str(self.remote)
            return super()._git(directory, *arguments, env=env)
        return super()._git(directory, *args, env=env)

    def _remote_head(self, full_name: str) -> str | None:
        sha = super()._remote_head(full_name)
        if sha and self.fail_after_push:
            self.fail_after_push = False
            raise RuntimeError("GitHub response lost after successful push")
        return sha


@pytest.fixture
def starter(tmp_path: Path) -> Path:
    project = tmp_path / "starter"
    (project / "app").mkdir(parents=True)
    (project / "tests" / "exercise").mkdir(parents=True)
    (project / "app" / "main.py").write_text("def task():\n    return 'unsolved'\n")
    (project / "tests" / "exercise" / "test_task.py").write_text(
        "from app.main import task\n\ndef test_task():\n    assert task() == 'solved'\n"
    )
    (project / "README.md").write_text("Run the learner exercise\n")
    (project / "TASK.md").write_text("Implement task()\n")
    (project / "PEERS.md").write_text("Backend: app/main.py\n")
    scaffold = Path(__file__).resolve().parents[3] / "scaffold" / "requirements.txt"
    (project / "requirements.txt").write_bytes(scaffold.read_bytes())
    (project / "source.pdf").write_text("private source")
    (project / "reference_solution.py").write_text("private solution")
    return project


@pytest.fixture
def publisher(tmp_path: Path) -> LocalGitHubPublisher:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    return LocalGitHubPublisher(remote)


def test_publish_creates_one_private_learner_commit_without_private_artifacts(
    starter: Path, publisher: LocalGitHubPublisher,
) -> None:
    created: list[str] = []

    result = publisher.publish(starter, "module-123", "Webhook Orders", None, created.append)

    assert result.full_name == "learner/webhook-orders-module-123"
    assert result.commit_sha == git(publisher.remote, "rev-parse", "refs/heads/main")
    assert created == [result.full_name]
    assert publisher.creations == 1
    assert git(publisher.remote, "rev-list", "--count", "refs/heads/main") == "1"
    files = set(git(publisher.remote, "ls-tree", "-r", "--name-only", "main").splitlines())
    assert {"README.md", "TASK.md", "PEERS.md", "requirements.txt", "app/main.py", "tests/exercise/test_task.py"} <= files
    assert not files & {"source.pdf", "reference_solution.py"}


def test_publish_rejects_hidden_secret_in_learner_tree_before_creating_repository(
    starter: Path, publisher: LocalGitHubPublisher,
) -> None:
    (starter / "app" / ".env").write_text("SECRET=private")

    with pytest.raises(ValueError, match="Unsupported learner file"):
        publisher.publish(starter, "module-123", "Webhook Orders", None, lambda _: None)

    assert publisher.creations == 0


def test_first_publish_accepts_github_empty_repository_conflict(
    starter: Path, publisher: LocalGitHubPublisher,
) -> None:
    publisher.missing_ref_status = 409

    result = publisher.publish(starter, "module-123", "Webhook Orders", None, lambda _: None)

    assert result.commit_sha == git(publisher.remote, "rev-parse", "refs/heads/main")
    assert publisher.creations == 1
    assert publisher.pushes == 1


def test_retry_of_existing_empty_repository_accepts_github_conflict_without_duplicate_creation(
    starter: Path, publisher: LocalGitHubPublisher,
) -> None:
    publisher.missing_ref_status = 409

    def interrupted(_full_name: str) -> None:
        raise RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        publisher.publish(starter, "module-123", "Webhook Orders", None, interrupted)
    assert publisher.creations == 1
    assert publisher.pushes == 0

    result = publisher.publish(
        starter, "module-123", "Webhook Orders", "learner/webhook-orders-module-123", lambda _: None,
    )

    assert result.commit_sha == git(publisher.remote, "rev-parse", "refs/heads/main")
    assert publisher.creations == 1
    assert publisher.pushes == 1


@pytest.mark.parametrize("message", ["Branch conflict", 17])
def test_unrelated_or_malformed_github_conflict_stops_before_push(
    starter: Path, publisher: LocalGitHubPublisher, message: object,
) -> None:
    publisher.missing_ref_status = 409
    publisher.missing_ref_body = {"message": message}

    with pytest.raises(urllib.error.HTTPError) as error:
        publisher.publish(starter, "module-123", "Webhook Orders", None, lambda _: None)

    assert error.value.code == 409
    assert publisher.pushes == 0


def test_retry_reuses_created_repository_after_callback_failure(
    starter: Path, publisher: LocalGitHubPublisher,
) -> None:
    def interrupted(_full_name: str) -> None:
        raise RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        publisher.publish(starter, "module-123", "Webhook Orders", None, interrupted)

    result = publisher.publish(starter, "module-123", "Webhook Orders", None, lambda _: None)

    assert result.commit_sha == git(publisher.remote, "rev-parse", "refs/heads/main")
    assert publisher.creations == 1


def test_create_conflict_recovers_only_matching_private_repository(
    starter: Path, publisher: LocalGitHubPublisher,
) -> None:
    publisher.create_conflict_after_creation = True

    result = publisher.publish(starter, "module-123", "Webhook Orders", None, lambda _: None)

    assert result.commit_sha == git(publisher.remote, "rev-parse", "refs/heads/main")
    assert publisher.creations == 1


def test_retry_recognizes_successful_push_after_lost_response(
    starter: Path, publisher: LocalGitHubPublisher,
) -> None:
    publisher.fail_after_push = True
    with pytest.raises(RuntimeError, match="response lost"):
        publisher.publish(starter, "module-123", "Webhook Orders", None, lambda _: None)
    original = git(publisher.remote, "rev-parse", "refs/heads/main")

    result = publisher.publish(
        starter, "module-123", "Webhook Orders", "learner/webhook-orders-module-123", lambda _: None,
    )

    assert result.commit_sha == original
    assert publisher.creations == 1
    assert git(publisher.remote, "rev-list", "--count", "main") == "1"


def test_publish_refuses_unrelated_existing_branch(
    starter: Path, publisher: LocalGitHubPublisher, tmp_path: Path,
) -> None:
    publisher.publish(starter, "module-123", "Webhook Orders", None, lambda _: None)
    checkout = tmp_path / "unrelated"
    subprocess.run(["git", "clone", str(publisher.remote), str(checkout)], check=True, capture_output=True)
    git(checkout, "checkout", "main")
    (checkout / "README.md").write_text("Unrelated content")
    git(checkout, "add", "README.md")
    git(checkout, "-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-m", "Unrelated")
    git(checkout, "push", "origin", "main")
    unrelated_sha = git(publisher.remote, "rev-parse", "refs/heads/main")

    with pytest.raises(RuntimeError, match="unrelated content"):
        publisher.publish(
            starter, "module-123", "Webhook Orders", "learner/webhook-orders-module-123", lambda _: None,
        )

    assert git(publisher.remote, "rev-parse", "refs/heads/main") == unrelated_sha
