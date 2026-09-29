"""Validated outcome produced by the trusted pytest plugin."""

from pydantic import BaseModel, ConfigDict


class PytestReport(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    node_ids: list[str]
    failed_ids: list[str]
    assertion_failed_ids: list[str]
    has_error: bool
    has_skip_or_xfail: bool
