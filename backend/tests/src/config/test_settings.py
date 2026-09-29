from pathlib import Path

import pytest
from pydantic import ValidationError

from apprenticeship.config.settings import Settings


def test_settings_accepts_external_data_directory_without_creating_it(tmp_path: Path) -> None:
    data_dir = tmp_path / "artifacts"

    settings = Settings(data_dir=data_dir, docker_image="verifier:test")

    assert settings.data_dir == data_dir.resolve()
    assert not data_dir.exists()


def test_settings_rejects_project_data_directory_before_creating_it() -> None:
    project_root = Path(__file__).resolve().parents[4]
    data_dir = project_root / "backend" / "uncreated-artifacts"
    assert not data_dir.exists()

    with pytest.raises(ValidationError, match="outside the application project"):
        Settings(data_dir=data_dir, docker_image="verifier:test")

    assert not data_dir.exists()
