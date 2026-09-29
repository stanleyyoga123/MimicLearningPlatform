import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from apprenticeship.features.github_webhooks.webhook_event import WebhookEvent


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WebhookInboxRepository:
    def __init__(self, database_path: Path):
        self._database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS github_webhook_inbox (
                delivery_id TEXT PRIMARY KEY,
                repository_full_name TEXT NOT NULL,
                pr_number INTEGER NOT NULL,
                status TEXT NOT NULL,
                next_attempt_at TEXT NOT NULL,
                received_at TEXT NOT NULL,
                record TEXT NOT NULL
            )""")
            connection.execute("""CREATE INDEX IF NOT EXISTS github_webhook_ready
                ON github_webhook_inbox (status, next_attempt_at, received_at)""")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def enqueue(self, delivery_id: str, module_id: str, repository_full_name: str,
                installation_id: int, pr_number: int) -> tuple[WebhookEvent, bool]:
        now = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT record FROM github_webhook_inbox WHERE delivery_id=?", (delivery_id,)
            ).fetchone()
            if row:
                existing = WebhookEvent.model_validate_json(row["record"])
                if (existing.module_id != module_id
                        or existing.repository_full_name.lower() != repository_full_name.lower()
                        or existing.installation_id != installation_id
                        or existing.pr_number != pr_number):
                    raise ValueError("GitHub delivery ID was reused for a different pull request")
                if existing.status == "failed":
                    existing.status = "queued"
                    existing.attempts = 0
                    existing.error = None
                    existing.next_attempt_at = now
                    existing.updated_at = now
                    self._save(connection, existing)
                    return existing, True
                return existing, False
            event = WebhookEvent(
                delivery_id=delivery_id, module_id=module_id,
                repository_full_name=repository_full_name, installation_id=installation_id,
                pr_number=pr_number, status="queued", attempts=0,
                next_attempt_at=now, received_at=now, updated_at=now,
            )
            connection.execute(
                "INSERT INTO github_webhook_inbox VALUES (?, ?, ?, ?, ?, ?, ?)",
                (delivery_id, repository_full_name, pr_number, event.status,
                 now.isoformat(), now.isoformat(), event.model_dump_json()),
            )
        return event, True

    def get(self, delivery_id: str) -> WebhookEvent | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT record FROM github_webhook_inbox WHERE delivery_id=?", (delivery_id,)
            ).fetchone()
        return WebhookEvent.model_validate_json(row["record"]) if row else None

    def list_recent(self, limit: int = 100) -> list[WebhookEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT record FROM github_webhook_inbox ORDER BY received_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [WebhookEvent.model_validate_json(row["record"]) for row in rows]

    def claim_next(self) -> WebhookEvent | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT record FROM github_webhook_inbox WHERE status='queued' "
                "AND next_attempt_at<=? ORDER BY received_at LIMIT 1",
                (_now().isoformat(),),
            ).fetchone()
            if not row:
                return None
            event = WebhookEvent.model_validate_json(row["record"])
            event.status = "running"
            event.updated_at = _now()
            self._save(connection, event)
        return event

    def complete(self, event: WebhookEvent, *, ignored: bool = False,
                 reason: str | None = None) -> None:
        event.status = "ignored" if ignored else "completed"
        event.error = reason
        event.updated_at = _now()
        with self._connect() as connection:
            self._save(connection, event)

    def postpone(self, event: WebhookEvent, seconds: int = 10) -> None:
        now = _now()
        event.status = "queued"
        event.next_attempt_at = now + timedelta(seconds=seconds)
        event.updated_at = now
        with self._connect() as connection:
            self._save(connection, event)

    def fail(self, event: WebhookEvent, reason: str, *, retryable: bool) -> None:
        now = _now()
        event.attempts += 1
        event.error = reason[:500]
        event.updated_at = now
        if retryable and event.attempts < 5:
            event.status = "queued"
            event.next_attempt_at = now + timedelta(seconds=min(300, 2 ** event.attempts))
        else:
            event.status = "failed"
        with self._connect() as connection:
            self._save(connection, event)

    def retry(self, delivery_id: str) -> WebhookEvent | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT record FROM github_webhook_inbox WHERE delivery_id=?", (delivery_id,)
            ).fetchone()
            if not row:
                return None
            event = WebhookEvent.model_validate_json(row["record"])
            if event.status != "failed":
                raise ValueError("Only failed webhook deliveries can be retried")
            event.status = "queued"
            event.attempts = 0
            event.error = None
            event.next_attempt_at = _now()
            event.updated_at = _now()
            self._save(connection, event)
        return event

    def recover_interrupted(self) -> None:
        now = _now()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT record FROM github_webhook_inbox WHERE status='running'"
            ).fetchall()
            for row in rows:
                event = WebhookEvent.model_validate_json(row["record"])
                event.status = "queued"
                event.error = "Worker interrupted; delivery will be retried"
                event.next_attempt_at = now
                event.updated_at = now
                self._save(connection, event)

    @staticmethod
    def _save(connection: sqlite3.Connection, event: WebhookEvent) -> None:
        connection.execute(
            "UPDATE github_webhook_inbox SET status=?, next_attempt_at=?, record=? "
            "WHERE delivery_id=?",
            (event.status, event.next_attempt_at.isoformat(), event.model_dump_json(),
             event.delivery_id),
        )
