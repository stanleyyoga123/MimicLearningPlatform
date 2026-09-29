"""Authenticate a GitHub App and mint repository-scoped installation tokens."""

import json
import re
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from pydantic import ValidationError

from apprenticeship.clients.github_app_models import (
    GitHubAppMetadata,
    GitHubInstallation,
    GitHubInstallationToken,
)


class GitHubAppClient:
    def __init__(self, app_id: str, private_key_path: Path) -> None:
        if not app_id.isdecimal():
            raise ValueError("GITHUB_APP_ID must be a numeric GitHub App ID")
        try:
            private_key = private_key_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise RuntimeError("Could not read the GitHub App private key") from error
        self._app_id = app_id
        self._private_key = private_key
        self._tokens: dict[str, GitHubInstallationToken] = {}
        self._reviewer_login: str | None = None
        self._jwt()

    def reviewer_login(self) -> str:
        if self._reviewer_login is None:
            try:
                app = GitHubAppMetadata.model_validate(self._request("GET", "/app"))
            except ValidationError as error:
                raise RuntimeError("GitHub returned incomplete App details") from error
            self._reviewer_login = f"{app.slug}[bot]"
        return self._reviewer_login

    def installation_id(self, repository: str) -> int:
        self._validate_repository(repository)
        try:
            installation = GitHubInstallation.model_validate(
                self._request("GET", f"/repos/{repository}/installation")
            )
        except ValidationError as error:
            raise RuntimeError("GitHub returned incomplete App installation details") from error
        return installation.id

    def token_for(self, repository: str) -> str:
        self._validate_repository(repository)
        key = repository.lower()
        cached = self._tokens.get(key)
        if cached and cached.expires_at > datetime.now(timezone.utc) + timedelta(seconds=60):
            return cached.token.get_secret_value()

        installation_id = self.installation_id(repository)
        repository_name = repository.partition("/")[2]
        try:
            token = GitHubInstallationToken.model_validate(self._request(
                "POST", f"/app/installations/{installation_id}/access_tokens", {
                    "repositories": [repository_name],
                    "permissions": {"contents": "read", "pull_requests": "write"},
                },
            ))
        except ValidationError as error:
            raise RuntimeError("GitHub returned incomplete App installation token details") from error
        if (token.permissions.get("contents") not in {"read", "write"}
                or token.permissions.get("pull_requests") != "write"
                or token.expires_at <= datetime.now(timezone.utc) + timedelta(seconds=60)):
            raise RuntimeError("GitHub App installation lacks required review permissions or token lifetime")
        self._tokens[key] = token
        return token.token.get_secret_value()

    def _jwt(self) -> str:
        now = int(time.time())
        try:
            return jwt.encode(
                {"iat": now - 60, "exp": now + 540, "iss": self._app_id},
                self._private_key,
                algorithm="RS256",
            )
        except (jwt.PyJWTError, ValueError, TypeError) as error:
            raise RuntimeError("GitHub App private key is invalid") from error

    def _request(self, method: str, path: str, data: dict | None = None) -> object:
        request = urllib.request.Request(
            f"https://api.github.com{path}",
            data=json.dumps(data).encode("utf-8") if data is not None else None,
            method=method,
            headers={
                "Authorization": f"Bearer {self._jwt()}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404 and path.endswith("/installation"):
                raise RuntimeError("GitHub App is not installed on this repository") from error
            raise RuntimeError(f"GitHub App request failed (HTTP {error.code})") from error
        except urllib.error.URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise RuntimeError("GitHub App request timed out; retry this submission") from error
            raise RuntimeError("GitHub App request could not connect") from error
        except (TimeoutError, socket.timeout) as error:
            raise RuntimeError("GitHub App request timed out; retry this submission") from error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise RuntimeError("GitHub App returned malformed JSON; retry this submission") from error
        except OSError as error:
            raise RuntimeError("GitHub App request could not connect") from error

    @staticmethod
    def _validate_repository(repository: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Invalid GitHub repository")
