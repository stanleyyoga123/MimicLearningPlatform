"""The limited GitHub fields used after signature verification."""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class _Repository(BaseModel):
    model_config = ConfigDict(extra="ignore")
    full_name: str = Field(min_length=3, max_length=255)


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ref: str
    repo: _Repository


class _Pull(BaseModel):
    model_config = ConfigDict(extra="ignore")
    number: int = Field(gt=0)
    html_url: HttpUrl
    state: str
    draft: bool
    base: _Base


class _Installation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int = Field(gt=0)


class WebhookPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action: str
    number: int = Field(gt=0)
    repository: _Repository
    installation: _Installation
    pull_request: _Pull
