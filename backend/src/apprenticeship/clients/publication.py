"""GitHub publication result."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Publication:
    full_name: str
    repository_url: str
    commit_sha: str
