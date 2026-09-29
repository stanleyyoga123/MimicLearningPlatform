from pathlib import Path
import os

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)

    data_dir: Path
    github_token: str | None = Field(default=None, repr=False)
    github_app_id: str | None = None
    github_app_private_key_path: Path | None = Field(default=None, repr=False)
    github_webhook_secret: str | None = Field(default=None, repr=False)
    docker_image: str
    codex_binary: str = "codex"
    codex_model: str | None = None
    openrouter_api_key: str | None = Field(default=None, repr=False)
    openrouter_model: str = "z-ai/glm-5.3-flash"
    cors_origin: str = "http://localhost:5173"

    @model_validator(mode="after")
    def validate_github_app(self) -> "Settings":
        if bool(self.github_app_id) != bool(self.github_app_private_key_path):
            raise ValueError("Set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY_PATH together")
        if self.github_app_private_key_path:
            key_path = self.github_app_private_key_path.expanduser().resolve()
            project_root = Path(__file__).resolve().parents[4]
            if key_path.is_relative_to(self.data_dir) or key_path.is_relative_to(project_root):
                raise ValueError("GitHub App private key must be outside the project and APP_DATA_DIR")
            self.github_app_private_key_path = key_path
        return self

    @field_validator("data_dir")
    @classmethod
    def require_external_data_dir(cls, value: Path) -> Path:
        resolved = value.expanduser().resolve()
        project_root = Path(__file__).resolve().parents[4]
        if resolved.is_relative_to(project_root):
            raise ValueError("APP_DATA_DIR must be outside the application project")
        return resolved

    @classmethod
    def from_environment(cls) -> "Settings":
        required = ("APP_DATA_DIR", "DOCKER_IMAGE")
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        return cls(
            data_dir=Path(os.environ["APP_DATA_DIR"]),
            github_token=os.environ.get("GITHUB_TOKEN") or None,
            github_app_id=os.environ.get("GITHUB_APP_ID") or None,
            github_app_private_key_path=(
                Path(os.environ["GITHUB_APP_PRIVATE_KEY_PATH"])
                if os.environ.get("GITHUB_APP_PRIVATE_KEY_PATH") else None
            ),
            github_webhook_secret=os.environ.get("GITHUB_WEBHOOK_SECRET") or None,
            docker_image=os.environ["DOCKER_IMAGE"],
            codex_binary=os.environ.get("CODEX_BINARY", "codex"),
            codex_model=os.environ.get("CODEX_MODEL") or None,
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY") or None,
            openrouter_model=os.environ.get("OPENROUTER_MODEL") or "z-ai/glm-5.3-flash",
            cors_origin=os.environ.get("CORS_ORIGIN", "http://localhost:5173"),
        )
