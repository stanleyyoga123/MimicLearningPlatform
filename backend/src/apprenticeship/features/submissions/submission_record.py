from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReviewFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Literal["high", "medium", "low"]
    blocking: bool
    body: str = Field(min_length=10, max_length=2000)
    path: str | None = None
    line: int | None = Field(default=None, ge=1)
    side: Literal["LEFT", "RIGHT"] | None = None


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=10, max_length=4000)
    findings: list[ReviewFinding] = Field(max_length=30)


class SubmissionRecord(BaseModel):
    id: str
    module_id: str
    repository_full_name: str
    pr_number: int
    pr_url: str
    pr_title: str
    base_sha: str
    head_sha: str
    created_at: datetime
    updated_at: datetime
    status: Literal["queued", "running", "needs_review", "success", "failed", "outdated"]
    stage: Literal["queued", "fetching", "reviewing", "publishing", "completed"]
    error: str | None = None
    findings: list[ReviewFinding] = Field(default_factory=list)
    summary: str | None = None
    github_review_id: int | None = None
    github_review_url: str | None = None
