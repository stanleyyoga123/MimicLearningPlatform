from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModuleSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=100)
    scenario: str = Field(min_length=10)
    learning_objective: str = Field(min_length=3)
    task_type: Literal["bugfix", "feature"]
    task_brief: str = Field(min_length=10)
    expected_behavior: str = Field(min_length=10)
    acceptance_criteria: list[str] = Field(min_length=1, max_length=6)
    simplifications: list[str]
