from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class GitHubPullRef(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    ref: str


class GitHubPullUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    login: str


class GitHubPull(BaseModel):
    model_config = ConfigDict(extra="ignore")

    number: int
    title: str
    html_url: HttpUrl
    state: Literal["open", "closed"]
    draft: bool
    base: GitHubPullRef
    head: GitHubPullRef
    user: GitHubPullUser


class PublishedReview(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    html_url: HttpUrl
    body: str | None = None
    commit_id: str
    user: GitHubPullUser
    state: str


@dataclass(frozen=True)
class ReviewSnapshot:
    workspace: Path
    diff: str
    changed_lines: frozenset[tuple[str, int, str]]
    changed_paths: frozenset[str]
