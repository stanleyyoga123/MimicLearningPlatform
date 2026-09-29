from pydantic import BaseModel, ConfigDict, Field


class PeerPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2)
    role: str = Field(min_length=2)
    contribution_history: str = Field(min_length=5)
    responsibilities: list[str] = Field(min_length=1)
    owned_files: list[str] = Field(min_length=1)
