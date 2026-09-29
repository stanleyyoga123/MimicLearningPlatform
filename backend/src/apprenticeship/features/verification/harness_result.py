"""Validated output from the trusted container harness."""

from typing import Literal

from pydantic import BaseModel, Field


class HarnessResult(BaseModel):
    status: Literal["passed", "failed", "assertion_failed", "timeout", "unavailable", "container_error", "invalid_report"]
    collected: int = Field(ge=0)
    failed: int = Field(ge=0)
    node_ids: list[str]
    failed_ids: list[str]
    detail: str
