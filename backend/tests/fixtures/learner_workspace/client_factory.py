"""Build an API test client with isolated storage and a controlled clock."""

from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from apprenticeship.config.settings import Settings
from apprenticeship.features.learner_workspace.chat_session_service import ChatModel
from apprenticeship.main import create_app


def client_for(
    data_dir: Path, model: ChatModel | None, clock: Callable[[], float] | None = None,
) -> TestClient:
    settings = Settings(data_dir=data_dir, docker_image="test-image")
    return TestClient(create_app(
        settings, chat_client=model, chat_clock=clock if clock is not None else lambda: 100.0,
    ))
