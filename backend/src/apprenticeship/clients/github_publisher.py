"""Publish the learner starter to a private personal GitHub repository."""

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from pydantic import ValidationError

from apprenticeship.clients.github_responses import (
    GitHubCommit,
    GitHubErrorResponse,
    GitHubReference,
    GitHubRepository,
    GitHubUser,
)
from apprenticeship.clients.publication import Publication


_ALLOWED_ROOTS = frozenset({
    "app", "tests", "README.md", "TASK.md", "PEERS.md",
    "requirements.txt", ".gitignore",
})
_CACHE_DIRECTORIES = frozenset({"__pycache__", ".pytest_cache"})
_HELPER = '!f() { printf "username=x-access-token\\npassword=%s\\n" "$APPRENTICESHIP_PUSH_TOKEN"; }; f'


class GitHubPublisher:
    def __init__(self, token: str) -> None:
        if not token:
            raise ValueError("A GitHub token is required")
        self._token = token

    def publish(
        self,
        starter: Path,
        module_id: str,
        title: str,
        existing_full_name: str | None,
        on_repository_created: Callable[[str], None],
    ) -> Publication:
        if not re.fullmatch(r"[a-zA-Z0-9-]+", module_id):
            raise ValueError("Invalid module ID")
        account = GitHubUser.model_validate(self._request("GET", "/user"))
        login = account.login
        name = self._repository_name(title, module_id)
        full_name = f"{login}/{name}"
        if existing_full_name and existing_full_name != full_name:
            raise ValueError("Saved repository does not match this module")
        with tempfile.TemporaryDirectory(prefix="apprenticeship-publish-") as temp:
            export = Path(temp) / "export"
            export.mkdir()
            self._export(starter, export)
            self._git(export, "init", "-b", "main")
            self._git(export, "add", "--force", "--all")
            self._git(export, "-c", "user.name=Apprenticeship Platform", "-c", "user.email=apprenticeship@localhost", "commit", "-m", f"Apprenticeship module {module_id}")
            local_tree = self._git(export, "rev-parse", "HEAD^{tree}").strip()
            repository = self._ensure_repository(full_name, name, module_id)
            if not existing_full_name:
                on_repository_created(full_name)
            remote_sha = self._remote_head(full_name)
            if remote_sha:
                commit = GitHubCommit.model_validate(self._request("GET", f"/repos/{full_name}/git/commits/{remote_sha}"))
                if commit.tree.sha != local_tree or commit.message != f"Apprenticeship module {module_id}":
                    raise RuntimeError("Repository already has unrelated content; publication stopped")
                return Publication(full_name, str(repository.html_url), remote_sha)
            env = self._git_env()
            env["APPRENTICESHIP_PUSH_TOKEN"] = self._token
            self._git(
                export, "-c", f"credential.helper={_HELPER}",
                "push", f"https://github.com/{full_name}.git", "HEAD:refs/heads/main", env=env,
            )
            commit_sha = self._remote_head(full_name)
            if not commit_sha:
                raise RuntimeError("Push completed but GitHub has no main branch")
            return Publication(full_name, str(repository.html_url), commit_sha)

    def _ensure_repository(self, full_name: str, name: str, module_id: str) -> GitHubRepository:
        marker = f"apprenticeship-module:{module_id}"
        try:
            repository = GitHubRepository.model_validate(self._request("GET", f"/repos/{full_name}"))
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            try:
                repository = GitHubRepository.model_validate(self._request("POST", "/user/repos", {
                    "name": name, "private": True, "auto_init": False, "description": marker,
                }))
            except urllib.error.HTTPError as create_error:
                if create_error.code != 422:
                    raise
                repository = GitHubRepository.model_validate(self._request("GET", f"/repos/{full_name}"))
        if repository.full_name != full_name or not repository.private or repository.description != marker:
            raise RuntimeError("Repository ownership marker or privacy does not match this module")
        if str(repository.html_url).rstrip("/") != f"https://github.com/{full_name}":
            raise RuntimeError("Repository URL does not match this module")
        return repository

    def _remote_head(self, full_name: str) -> str | None:
        try:
            response = GitHubReference.model_validate(self._request("GET", f"/repos/{full_name}/git/ref/heads/main"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code == 409:
                try:
                    error = GitHubErrorResponse.model_validate_json(exc.read())
                except ValidationError:
                    raise exc
                # GitHub cannot look up refs until the first commit is pushed.
                if error.message == "Git Repository is empty.":
                    return None
            raise
        return response.object.sha

    def _request(self, method: str, path: str, data: dict | None = None) -> dict:
        body = json.dumps(data).encode("utf-8") if data is not None else None
        request = urllib.request.Request(
            f"https://api.github.com{path}", data=body, method=method,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    @staticmethod
    def _repository_name(title: str, module_id: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48].rstrip("-")
        return f"{slug or 'module'}-{module_id}"

    @staticmethod
    def _export(starter: Path, export: Path) -> None:
        if not starter.is_dir():
            raise ValueError("Starter directory is missing")
        for entry in starter.iterdir():
            if entry.name not in _ALLOWED_ROOTS:
                continue
            if entry.is_symlink():
                raise ValueError(f"Symlink cannot be published: {entry.name}")
            if entry.is_file():
                shutil.copy2(entry, export / entry.name)
                continue
            if not entry.is_dir():
                raise ValueError(f"Unsupported learner artifact: {entry.name}")
            for root, directories, files in os.walk(entry, followlinks=False):
                source = Path(root)
                relative = source.relative_to(starter)
                directories[:] = [name for name in directories if name not in _CACHE_DIRECTORIES]
                for name in directories:
                    if name.startswith("."):
                        raise ValueError(f"Hidden learner directory cannot be published: {relative / name}")
                    if (source / name).is_symlink():
                        raise ValueError(f"Symlink cannot be published: {relative / name}")
                (export / relative).mkdir(parents=True, exist_ok=True)
                for name in files:
                    path = source / name
                    if path.is_symlink():
                        raise ValueError(f"Symlink cannot be published: {relative / name}")
                    if name.startswith(".") or name.endswith((".pyc", ".log")):
                        raise ValueError(f"Unsupported learner file cannot be published: {relative / name}")
                    shutil.copy2(path, export / relative / name)
        if not (export / "README.md").is_file() or not (export / "app").is_dir() or not (export / "tests").is_dir():
            raise ValueError("Starter is missing required learner files")
        requirements = export / "requirements.txt"
        trusted_requirements = Path(__file__).resolve().parents[3] / "scaffold" / "requirements.txt"
        if not requirements.is_file() or requirements.read_bytes() != trusted_requirements.read_bytes():
            raise ValueError("Starter dependencies must match the fixed scaffold")

    @staticmethod
    def _git_env() -> dict[str, str]:
        allowed = {"PATH", "HOME", "USER", "TMPDIR", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR"}
        env = {key: value for key, value in os.environ.items() if key in allowed}
        env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"})
        return env

    @classmethod
    def _git(cls, directory: Path, *args: str, env: dict[str, str] | None = None) -> str:
        command = ["git", "-c", "core.hooksPath=/dev/null", *args]
        result = subprocess.run(command, cwd=directory, env=env or cls._git_env(), text=True, capture_output=True, timeout=90)
        if result.returncode:
            raise RuntimeError(f"Git operation failed: {args[-1] if args else 'unknown'}")
        return result.stdout
