from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WebhookEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_id: str
    module_id: str
    repository_full_name: str
    installation_id: int = Field(gt=0)
    pr_number: int = Field(gt=0)
    status: Literal["queued", "running", "completed", "ignored", "failed"]
    attempts: int = 0
    next_attempt_at: datetime
    received_at: datetime
    updated_at: datetime
    error: str | None = None
