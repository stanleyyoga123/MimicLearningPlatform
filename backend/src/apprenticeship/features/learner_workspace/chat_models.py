"""Public request and response models for learner conversations."""

from pydantic import BaseModel, Field, field_validator


class ChatAgent(BaseModel):
    id: str
    name: str
    role: str
    description: str


class ChatSessionView(BaseModel):
    id: str
    module_id: str
    agents: list[ChatAgent]
    expires_in_seconds: int


class SendMessageRequest(BaseModel):
    agent_id: str
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content", mode="before")
    @classmethod
    def require_nonblank_content(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Message must be text")
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message cannot be blank")
        return stripped


class ChatReply(BaseModel):
    agent_id: str
    content: str
