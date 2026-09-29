"""Temporary learner conversations stream progress and preserve session boundaries."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from apprenticeship.clients.openrouter_client import OpenRouterFailure, OpenRouterTimeout
from apprenticeship.config.settings import Settings
from apprenticeship.features.modules.module_repository import ModuleRepository
from apprenticeship.main import create_app
from tests.fixtures.learner_workspace.blocking_model import BlockingModel
from tests.fixtures.learner_workspace.client_factory import client_for
from tests.fixtures.learner_workspace.published_module import published_module
from tests.fixtures.learner_workspace.recording_model import RecordingModel


def events(response: httpx.Response) -> list[dict[str, object]]:
    assert response.headers["content-type"].startswith("application/x-ndjson")
    return [json.loads(line) for line in response.text.splitlines()]


def test_session_creation_requires_published_module_and_configured_chat(tmp_path: Path) -> None:
    model = RecordingModel()
    client = client_for(tmp_path, model)
    assert client.post("/modules/missing/sessions").status_code == 404
    queued_id = ModuleRepository(tmp_path / "modules.sqlite3").create("queued-module").id
    assert client.post(f"/modules/{queued_id}/sessions").status_code == 409
    module_id = published_module(tmp_path)

    assert client_for(tmp_path, None).post(f"/modules/{module_id}/sessions").status_code == 503
    assert model.calls == []


def test_streamed_agents_have_separate_history_and_only_bounded_learner_context(
    tmp_path: Path,
) -> None:
    module_id = published_module(tmp_path)
    model = RecordingModel([["Try the ", "duplicate delivery test."]] * 4)
    client = client_for(tmp_path, model)
    before = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}

    created = client.post(f"/modules/{module_id}/sessions")
    assert created.status_code == 201
    view = created.json()
    assert view["module_id"] == module_id
    assert view["expires_in_seconds"] == 90
    assert [agent["id"] for agent in view["agents"]] == ["peer-0", "peer-1", "mentor"]
    assert "backend-only-fact" not in created.text
    session_id = view["id"]
    for agent_id, question in (
        ("peer-0", "peer-zero-question-384"),
        ("peer-1", "peer-one-question-539"),
        ("mentor", "mentor-question-706"),
        ("peer-0", "peer-zero-followup-118"),
    ):
        response = client.post(
            f"/sessions/{session_id}/messages", json={"agent_id": agent_id, "content": question},
        )
        assert response.status_code == 200
        assert events(response) == [
            {"type": "delta", "agent_id": agent_id, "content": "Try the "},
            {"type": "delta", "agent_id": agent_id, "content": "duplicate delivery test."},
            {"type": "done", "agent_id": agent_id},
        ]

    systems = [call[0].content for call in model.calls]
    assert "backend-only-fact-481" in systems[0]
    assert "starter-route-marker-184" in systems[0]
    assert "qa-only-fact-729" not in systems[0]
    assert "qa-only-fact-729" in systems[1]
    assert "qa-fixture-marker-531" in systems[1]
    assert "backend-only-fact-481" not in systems[1]
    assert "Duplicate webhook orders" in systems[2]
    assert "backend-only-fact-481" not in systems[2]
    assert "qa-only-fact-729" not in systems[2]
    for call in model.calls:
        contents = "\n".join(message.content for message in call)
        assert "private-source-marker-914" not in contents
        assert "private-log-marker-642" not in contents
        assert "private-reference-marker-377" not in contents
    assert "peer-zero-question-384" not in "\n".join(m.content for m in model.calls[1])
    assert "peer-one-question-539" not in "\n".join(m.content for m in model.calls[2])
    assert [message.role for message in model.calls[3]] == ["system", "user", "assistant", "user"]
    assert model.calls[3][1].content == "peer-zero-question-384"
    assert model.calls[3][2].content == "Try the duplicate delivery test."
    assert {path.relative_to(tmp_path) for path in tmp_path.rglob("*")} == before


def test_heartbeat_extends_expiry_and_close_is_idempotent(tmp_path: Path) -> None:
    module_id = published_module(tmp_path)
    now = [100.0]
    client = client_for(tmp_path, RecordingModel(), lambda: now[0])
    session_id = client.post(f"/modules/{module_id}/sessions").json()["id"]

    now[0] = 189.0
    assert client.post(f"/sessions/{session_id}/heartbeat").status_code == 204
    now[0] = 278.0
    assert events(client.post(
        f"/sessions/{session_id}/messages", json={"agent_id": "mentor", "content": "Help"},
    ))[-1] == {"type": "done", "agent_id": "mentor"}
    now[0] = 280.0
    assert client.post(f"/sessions/{session_id}/heartbeat").status_code == 404
    assert client.post(f"/sessions/{session_id}/close").status_code == 204
    assert client.post(f"/sessions/{session_id}/close").status_code == 204
    assert client.post(
        f"/sessions/{session_id}/messages", json={"agent_id": "mentor", "content": "Help"},
    ).status_code == 404


def test_invalid_input_fails_preflight_and_partial_provider_errors_do_not_poison_history(
    tmp_path: Path,
) -> None:
    module_id = published_module(tmp_path)
    model = RecordingModel([
        ["partial", OpenRouterTimeout("OpenRouter timed out. Try sending the message again.")],
        ["partial", OpenRouterFailure("OpenRouter could not complete the message. Try again.")],
        ["Continue from the exercise test."],
    ])
    client = client_for(tmp_path, model)
    session_id = client.post(f"/modules/{module_id}/sessions").json()["id"]
    endpoint = f"/sessions/{session_id}/messages"
    assert client.post(endpoint, json={"agent_id": "mentor", "content": "   "}).status_code == 422
    assert client.post(endpoint, json={"agent_id": "mentor", "content": "x" * 4001}).status_code == 422
    assert client.post(endpoint, json={"agent_id": "missing", "content": "Help"}).status_code == 422
    assert model.calls == []

    timed_out = events(client.post(
        endpoint, json={"agent_id": "mentor", "content": "failed-on-timeout"},
    ))
    failed = events(client.post(
        endpoint, json={"agent_id": "mentor", "content": "failed-on-error"},
    ))
    succeeded = events(client.post(
        endpoint, json={"agent_id": "mentor", "content": "  " + "x" * 4000 + "  "},
    ))

    assert timed_out[0] == {"type": "delta", "agent_id": "mentor", "content": "partial"}
    assert timed_out[-1] == {
        "type": "error", "agent_id": "mentor", "detail": "OpenRouter timed out. Try sending the message again.",
        "status": 504,
    }
    assert failed[-1]["type"] == "error"
    assert failed[-1]["status"] == 502
    assert succeeded == [
        {"type": "delta", "agent_id": "mentor", "content": "Continue from the exercise test."},
        {"type": "done", "agent_id": "mentor"},
    ]
    assert [message.role for message in model.calls[2]] == ["system", "user"]
    assert model.calls[2][-1].content == "x" * 4000


@pytest.mark.parametrize("termination", ["close", "expiry"])
def test_busy_request_is_rejected_and_ending_session_cancels_inflight_provider(
    tmp_path: Path, termination: str,
) -> None:
    module_id = published_module(tmp_path)
    now = [100.0]

    async def exercise() -> None:
        model = BlockingModel()
        app = create_app(
            Settings(data_dir=tmp_path, docker_image="test-image"),
            chat_client=model, chat_clock=lambda: now[0],
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            session_id = (await client.post(f"/modules/{module_id}/sessions")).json()["id"]
            endpoint = f"/sessions/{session_id}/messages"
            first = asyncio.create_task(client.post(
                endpoint, json={"agent_id": "peer-0", "content": "First question"},
            ))
            await asyncio.wait_for(model.started.wait(), timeout=2)

            busy = await client.post(
                endpoint, json={"agent_id": "peer-1", "content": "Second question"},
            )
            assert busy.status_code == 409
            if termination == "expiry":
                now[0] = 191.0
                ended = await client.post(f"/sessions/{session_id}/heartbeat")
                assert ended.status_code == 404
            else:
                ended = await client.post(f"/sessions/{session_id}/close")
                assert ended.status_code == 204

            assert events(await first)[-1] == {
                "type": "error", "agent_id": "peer-0", "detail": "Workspace session has ended",
                "status": 404,
            }
            assert model.cancelled.is_set()
            assert (await client.post(
                endpoint, json={"agent_id": "peer-0", "content": "After end"},
            )).status_code == 404

    asyncio.run(exercise())
