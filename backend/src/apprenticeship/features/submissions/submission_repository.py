import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from apprenticeship.features.submissions.submission_record import SubmissionRecord


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SubmissionRepository:
    def __init__(self, database_path: Path):
        self._database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY,
                module_id TEXT NOT NULL,
                repository_full_name TEXT NOT NULL,
                pr_number INTEGER NOT NULL,
                base_sha TEXT NOT NULL,
                head_sha TEXT NOT NULL,
                created_at TEXT NOT NULL,
                record TEXT NOT NULL
            )""")
            connection.execute("""CREATE INDEX IF NOT EXISTS submissions_module_created
                ON submissions (module_id, created_at DESC)""")
            connection.execute("""CREATE UNIQUE INDEX IF NOT EXISTS submissions_revision
                ON submissions (module_id, pr_number, base_sha, head_sha)""")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def create_or_get(self, submission: SubmissionRecord) -> SubmissionRecord:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT record FROM submissions WHERE module_id=? AND pr_number=? "
                "AND base_sha=? AND head_sha=?",
                (submission.module_id, submission.pr_number, submission.base_sha, submission.head_sha),
            ).fetchone()
            existing = SubmissionRecord.model_validate_json(row["record"]) if row else None
            if existing and existing.status != "outdated":
                return existing
            active = connection.execute(
                "SELECT id FROM submissions WHERE module_id=? AND pr_number=? "
                "AND json_extract(record, '$.status') IN ('queued', 'running')",
                (submission.module_id, submission.pr_number),
            ).fetchone()
            if active:
                raise ValueError("A review for this pull request is already in progress")
            if existing:
                # SubmissionService has revalidated the current PR. A reopened PR
                # may have the same revision as a review stopped while it was closed.
                existing.status = "queued"
                existing.stage = "queued"
                existing.error = None
                existing.updated_at = _now()
                connection.execute(
                    "UPDATE submissions SET record=? WHERE id=?",
                    (existing.model_dump_json(), existing.id),
                )
                return existing
            connection.execute(
                "INSERT INTO submissions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (submission.id, submission.module_id, submission.repository_full_name,
                 submission.pr_number, submission.base_sha, submission.head_sha,
                 submission.created_at.isoformat(), submission.model_dump_json()),
            )
        return submission

    def get(self, submission_id: str) -> SubmissionRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT record FROM submissions WHERE id=?", (submission_id,)
            ).fetchone()
        return SubmissionRecord.model_validate_json(row["record"]) if row else None

    def list_for_module(self, module_id: str) -> list[SubmissionRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT record FROM submissions WHERE module_id=? ORDER BY created_at DESC",
                (module_id,),
            ).fetchall()
        return [SubmissionRecord.model_validate_json(row["record"]) for row in rows]

    def save(self, submission: SubmissionRecord) -> SubmissionRecord:
        submission.updated_at = _now()
        with self._connect() as connection:
            connection.execute(
                "UPDATE submissions SET record=? WHERE id=?",
                (submission.model_dump_json(), submission.id),
            )
        return submission

    def claim_next(self) -> SubmissionRecord | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT record FROM submissions WHERE json_extract(record, '$.status')='queued' "
                "ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            submission = SubmissionRecord.model_validate_json(row["record"])
            submission.status = "running"
            submission.updated_at = _now()
            connection.execute(
                "UPDATE submissions SET record=? WHERE id=?",
                (submission.model_dump_json(), submission.id),
            )
        return submission

    def fail_interrupted(self) -> None:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT record FROM submissions WHERE json_extract(record, '$.status')='running'"
            ).fetchall()
            for row in rows:
                submission = SubmissionRecord.model_validate_json(row["record"])
                submission.status = "failed"
                submission.error = "Worker stopped during review. Retry this submission to continue."
                submission.updated_at = _now()
                connection.execute(
                    "UPDATE submissions SET record=? WHERE id=?",
                    (submission.model_dump_json(), submission.id),
                )

    def retry(self, submission_id: str) -> SubmissionRecord | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT record FROM submissions WHERE id=?", (submission_id,)
            ).fetchone()
            if row is None:
                return None
            submission = SubmissionRecord.model_validate_json(row["record"])
            if submission.status != "failed":
                raise ValueError("Only failed reviews can be retried")
            active = connection.execute(
                "SELECT id FROM submissions WHERE module_id=? AND pr_number=? AND id<>? "
                "AND json_extract(record, '$.status') IN ('queued', 'running')",
                (submission.module_id, submission.pr_number, submission.id),
            ).fetchone()
            if active:
                raise ValueError("A review for this pull request is already in progress")
            submission.status = "queued"
            submission.error = None
            submission.updated_at = _now()
            connection.execute(
                "UPDATE submissions SET record=? WHERE id=?",
                (submission.model_dump_json(), submission.id),
            )
        return submission

    @staticmethod
    def new(module_id: str, repository_full_name: str, pr_number: int, pr_url: str,
            pr_title: str, base_sha: str, head_sha: str) -> SubmissionRecord:
        now = _now()
        return SubmissionRecord(
            id=uuid4().hex, module_id=module_id, repository_full_name=repository_full_name,
            pr_number=pr_number, pr_url=pr_url, pr_title=pr_title,
            base_sha=base_sha, head_sha=head_sha, created_at=now, updated_at=now,
            status="queued", stage="queued",
        )
