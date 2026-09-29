import sqlite3
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit
from uuid import uuid4

from apprenticeship.features.modules.module_record import ModuleRecord


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ModuleRepository:
    def __init__(self, database_path: Path):
        self._database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS modules (
                    id TEXT PRIMARY KEY,
                    record TEXT NOT NULL,
                    repository_full_name TEXT,
                    created_at TEXT NOT NULL
                )"""
            )
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(modules)").fetchall()
            }
            if "repository_full_name" not in columns:
                connection.execute("ALTER TABLE modules ADD COLUMN repository_full_name TEXT")
            rows = connection.execute(
                "SELECT id, record FROM modules "
                "WHERE repository_full_name IS NULL OR repository_full_name = ''"
            ).fetchall()
            for row in rows:
                module = ModuleRecord.model_validate_json(row["record"])
                full_name = self._repository_name_from_url(module.repository_url)
                if full_name:
                    connection.execute(
                        "UPDATE modules SET repository_full_name = ? WHERE id = ?",
                        (full_name, row["id"]),
                    )

    @staticmethod
    def _repository_name_from_url(repository_url: str | None) -> str | None:
        if not repository_url:
            return None
        parsed = urlsplit(repository_url)
        if (parsed.scheme != "https" or parsed.netloc.lower() != "github.com"
                or parsed.query or parsed.fragment):
            return None
        match = re.fullmatch(r"/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/?", parsed.path)
        return f"{match.group(1)}/{match.group(2)}" if match else None

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def create(self, module_id: str | None = None) -> ModuleRecord:
        module = ModuleRecord(
            id=module_id or uuid4().hex,
            title="New module",
            status="queued",
            stage="queued",
            created_at=_now(),
            updated_at=_now(),
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO modules (id, record, created_at) VALUES (?, ?, ?)",
                (module.id, module.model_dump_json(), module.created_at.isoformat()),
            )
        return module

    def get(self, module_id: str) -> ModuleRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT record FROM modules WHERE id = ?", (module_id,)).fetchone()
        return ModuleRecord.model_validate_json(row["record"]) if row else None

    def list(self) -> list[ModuleRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT record FROM modules ORDER BY created_at DESC"
            ).fetchall()
        return [ModuleRecord.model_validate_json(row["record"]) for row in rows]

    def save(self, module: ModuleRecord) -> ModuleRecord:
        module.updated_at = _now()
        with self._connect() as connection:
            connection.execute(
                "UPDATE modules SET record = ? WHERE id = ?",
                (module.model_dump_json(), module.id),
            )
        return module

    def claim_next(self) -> ModuleRecord | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT record FROM modules WHERE json_extract(record, '$.status') = 'queued' "
                "ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            module = ModuleRecord.model_validate_json(row["record"])
            module.status = "running"
            module.updated_at = _now()
            connection.execute(
                "UPDATE modules SET record = ? WHERE id = ?",
                (module.model_dump_json(), module.id),
            )
        return module

    def fail_interrupted(self) -> None:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT record FROM modules WHERE json_extract(record, '$.status') = 'running'"
            ).fetchall()
            for row in rows:
                module = ModuleRecord.model_validate_json(row["record"])
                module.status = "failed"
                module.error = "Worker stopped during generation. Retry this module to continue."
                module.updated_at = _now()
                connection.execute(
                    "UPDATE modules SET record = ? WHERE id = ?",
                    (module.model_dump_json(), module.id),
                )

    def retry(self, module_id: str) -> ModuleRecord | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT record FROM modules WHERE id = ?", (module_id,)).fetchone()
            if row is None:
                return None
            module = ModuleRecord.model_validate_json(row["record"])
            if module.status != "failed":
                raise ValueError("Only failed modules can be retried")
            module.status = "queued"
            module.error = None
            module.updated_at = _now()
            connection.execute(
                "UPDATE modules SET record = ? WHERE id = ?",
                (module.model_dump_json(), module.id),
            )
        return module

    def repository_full_name(self, module_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT repository_full_name FROM modules WHERE id = ?", (module_id,)
            ).fetchone()
        return row["repository_full_name"] if row else None

    def find_by_repository_full_name(self, full_name: str) -> ModuleRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT record FROM modules WHERE repository_full_name = ? COLLATE NOCASE",
                (full_name,),
            ).fetchone()
        return ModuleRecord.model_validate_json(row["record"]) if row else None

    def save_repository_full_name(self, module_id: str, full_name: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE modules SET repository_full_name = ? WHERE id = ?",
                (full_name, module_id),
            )
