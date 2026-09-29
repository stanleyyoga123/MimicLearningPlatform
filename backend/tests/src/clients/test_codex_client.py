"""Codex process boundary tests."""

from pathlib import Path

import pytest

from apprenticeship.clients.codex_client import CodexClient


@pytest.mark.parametrize(
    ("operation", "sandbox"),
    [("generate", "workspace-write"), ("review", "read-only")],
)
def test_codex_invocation_uses_expected_sandbox_and_excludes_service_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str, sandbox: str,
) -> None:
    binary = tmp_path / "fake-codex"
    binary.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, pathlib, sys\n"
        "assert not any(key in os.environ for key in "
        "('GITHUB_TOKEN', 'GITHUB_APP_ID', 'GITHUB_APP_PRIVATE_KEY_PATH', "
        "'GITHUB_WEBHOOK_SECRET', 'GH_TOKEN', 'OPENROUTER_API_KEY'))\n"
        f"assert sys.argv[sys.argv.index('--sandbox')+1] == {sandbox!r}\n"
        "assert '--ignore-user-config' in sys.argv\n"
        "assert '--ignore-rules' in sys.argv\n"
        "pathlib.Path(sys.argv[sys.argv.index('-o')+1]).write_text(json.dumps({'ok': True}))\n"
        "print(json.dumps({'type': 'turn.completed'}))\n"
    )
    binary.chmod(0o755)
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("GITHUB_APP_ID", "12345")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", "/private/test-app-key.pem")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "webhook-secret")
    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret")
    workspace = tmp_path / "workspace"
    events: list[str] = []

    result = getattr(CodexClient(str(binary), None), operation)(
        "Create task", workspace, {"type": "object"}, workspace / "result.json", events.append,
    )

    assert result == {"ok": True}
    assert events == ["turn.completed"]


def test_generate_rejects_output_outside_workspace(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="workspace"):
        CodexClient("codex", None).generate("prompt", tmp_path / "work", {}, tmp_path / "other.json")
