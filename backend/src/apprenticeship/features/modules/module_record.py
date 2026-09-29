from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from apprenticeship.features.modules.module_spec import ModuleSpec
from apprenticeship.features.modules.peer_public import PeerPublic
from apprenticeship.features.verification.verification_report import VerificationReport


ModuleStage = Literal[
    "queued", "extracting", "specifying", "reference", "starter", "peers",
    "verifying", "publishing", "completed",
]


class ModuleRecord(BaseModel):
    id: str
    title: str
    status: Literal["queued", "running", "completed", "failed"]
    stage: ModuleStage
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    spec: ModuleSpec | None = None
    peers: list[PeerPublic] = Field(default_factory=list)
    verification: VerificationReport | None = None
    repository_url: str | None = None
    commit_sha: str | None = None
