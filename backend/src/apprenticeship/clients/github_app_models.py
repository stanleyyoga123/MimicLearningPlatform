"""Validated responses from GitHub App authentication endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class GitHubAppMetadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str = Field(pattern=r"^[A-Za-z0-9-]+$")


class GitHubInstallation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int = Field(gt=0)


class GitHubInstallationToken(BaseModel):
    model_config = ConfigDict(extra="ignore")

    token: SecretStr = Field(min_length=1)
    expires_at: datetime
    permissions: dict[str, str]

    @field_validator("expires_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("GitHub token expiry must include a timezone")
        return value
