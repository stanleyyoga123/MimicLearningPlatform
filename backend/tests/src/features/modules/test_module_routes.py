from pathlib import Path

from fastapi.testclient import TestClient

from apprenticeship.config.settings import Settings
from apprenticeship.main import create_app


def _client(tmp_path: Path) -> TestClient:
    settings = Settings(data_dir=tmp_path, docker_image="test-image")
    return TestClient(create_app(settings))


def test_submit_and_list_text_module(tmp_path: Path) -> None:
    client = _client(tmp_path)
    created = client.post("/modules", data={"text": "Duplicate webhook deliveries create two orders"})
    assert created.status_code == 202
    module_id = created.json()["id"]
    assert created.json()["status"] == "queued"
    assert client.get(f"/modules/{module_id}").json()["id"] == module_id
    assert [item["id"] for item in client.get("/modules").json()] == [module_id]
    assert (tmp_path / "modules" / module_id / "private" / "source.txt").read_text() == (
        "Duplicate webhook deliveries create two orders"
    )


def test_retry_requires_failed_status(tmp_path: Path) -> None:
    client = _client(tmp_path)
    module_id = client.post("/modules", data={"text": "Fix duplicate webhook orders"}).json()["id"]
    assert client.post(f"/modules/{module_id}/retry").status_code == 409


def test_upload_rejects_unsupported_type(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post("/modules", files={"file": ("input.py", b"pass")})
    assert response.status_code == 422
    assert client.get("/modules").json() == []


def test_cross_origin_submission_is_rejected(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/modules", data={"text": "Fix duplicate webhook orders"},
        headers={"Origin": "https://untrusted.example"},
    )
    assert response.status_code == 403
    assert client.get("/modules").json() == []
