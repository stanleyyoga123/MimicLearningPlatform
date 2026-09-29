"""GitHub App authentication at the HTTP boundary, without a live GitHub call."""

import io
import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from apprenticeship.clients.github_app_client import GitHubAppClient


@pytest.fixture
def app_key(tmp_path: Path) -> tuple[Path, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    path = tmp_path / "app.pem"
    path.write_bytes(private)
    return path, public


def test_app_signs_rs256_jwt_and_uses_bot_identity(
    app_key: tuple[Path, bytes], monkeypatch: pytest.MonkeyPatch,
) -> None:
    path, public = app_key
    requests: list[urllib.request.Request] = []

    def fake_urlopen(request: urllib.request.Request, timeout: int) -> io.BytesIO:
        requests.append(request)
        return io.BytesIO(b'{"slug":"exercise-reviewer"}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    app = GitHubAppClient("12345", path)

    assert app.reviewer_login() == "exercise-reviewer[bot]"
    assert app.reviewer_login() == "exercise-reviewer[bot]"
    assert len(requests) == 1
    assert requests[0].full_url == "https://api.github.com/app"
    assertion = jwt.decode(
        requests[0].get_header("Authorization").removeprefix("Bearer "),
        public,
        algorithms=["RS256"],
    )
    assert assertion["iss"] == "12345"
    assert assertion["exp"] - assertion["iat"] <= 600


def test_installation_tokens_are_scoped_by_repository_and_refreshed_before_expiry(
    app_key: tuple[Path, bytes], monkeypatch: pytest.MonkeyPatch,
) -> None:
    import apprenticeship.clients.github_app_client as app_module

    instant = datetime(2026, 9, 29, tzinfo=timezone.utc)

    class Clock(datetime):
        current = instant

        @classmethod
        def now(cls, tz: timezone | None = None) -> datetime:
            return cls.current

    monkeypatch.setattr(app_module, "datetime", Clock)
    issued: list[tuple[str, dict[str, object]]] = []

    def fake_urlopen(request: urllib.request.Request, timeout: int) -> io.BytesIO:
        if request.full_url.endswith("/installation"):
            return io.BytesIO(b'{"id":456}')
        assert request.full_url.endswith("/app/installations/456/access_tokens")
        payload = json.loads(request.data or b"{}")
        issued.append((request.full_url, payload))
        return io.BytesIO(json.dumps({
            "token": f"temporary-token-{len(issued)}",
            "expires_at": (Clock.current + timedelta(seconds=90)).isoformat(),
            "permissions": {"contents": "read", "pull_requests": "write"},
        }).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    app = GitHubAppClient("12345", app_key[0])

    assert app.token_for("owner/first") == "temporary-token-1"
    assert app.token_for("owner/first") == "temporary-token-1"
    assert app.token_for("owner/second") == "temporary-token-2"
    Clock.current += timedelta(seconds=31)
    assert app.token_for("owner/first") == "temporary-token-3"
    assert [body["repositories"] for _, body in issued] == [
        ["first"], ["second"], ["first"],
    ]
    assert all(body["permissions"] == {
        "contents": "read", "pull_requests": "write",
    } for _, body in issued)


def test_app_rejects_missing_installation_and_does_not_expose_upstream_body(
    app_key: tuple[Path, bytes], monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: int) -> io.BytesIO:
        raise urllib.error.HTTPError(
            request.full_url, 404, "private-secret-diagnostic", {},
            io.BytesIO(b"private-secret-response"),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    app = GitHubAppClient("12345", app_key[0])

    with pytest.raises(RuntimeError, match="not installed") as error:
        app.token_for("owner/exercise")

    assert "private-secret" not in str(error.value)


def test_app_rejects_installation_token_without_review_permission(
    app_key: tuple[Path, bytes], monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: int) -> io.BytesIO:
        if request.full_url.endswith("/installation"):
            return io.BytesIO(b'{"id":456}')
        return io.BytesIO(json.dumps({
            "token": "limited-token",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "permissions": {"contents": "read", "pull_requests": "read"},
        }).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    app = GitHubAppClient("12345", app_key[0])

    with pytest.raises(RuntimeError, match="permissions") as error:
        app.token_for("owner/exercise")

    assert "limited-token" not in str(error.value)
