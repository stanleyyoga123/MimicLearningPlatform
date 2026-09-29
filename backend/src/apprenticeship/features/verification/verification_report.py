"""Persistable verification results."""

from pydantic import BaseModel


class VerificationCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class VerificationReport(BaseModel):
    passed: bool
    summary: str
    checks: list[VerificationCheck]
