"""Validated fields consumed from GitHub's repository API."""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class GitHubUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    login: str = Field(min_length=1)


class GitHubErrorResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str


class GitHubRepository(BaseModel):
    model_config = ConfigDict(extra="ignore")

    full_name: str = Field(min_length=3)
    private: bool
    description: str | None
    html_url: HttpUrl


class GitHubObject(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class GitHubReference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    object: GitHubObject


class GitHubCommit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tree: GitHubObject
    message: str
