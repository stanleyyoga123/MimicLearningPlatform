import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from apprenticeship.features.modules.module_record import ModuleRecord
from apprenticeship.features.modules.module_repository import ModuleRepository


def test_worker_restart_marks_inflight_module_failed_and_retryable(tmp_path: Path) -> None:
    repository = ModuleRepository(tmp_path / "modules.sqlite3")
    created = repository.create()
    claimed = repository.claim_next()
    assert claimed is not None and claimed.id == created.id

    restarted = ModuleRepository(tmp_path / "modules.sqlite3")
    restarted.fail_interrupted()
    failed = restarted.get(created.id)
    assert failed is not None and failed.status == "failed"
    assert failed.error is not None and "Retry" in failed.error
    queued = restarted.retry(created.id)
    assert queued is not None and queued.status == "queued"


def _legacy_database(path: Path) -> tuple[str, str]:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    module = ModuleRecord(
        id="legacy-module", title="Existing exercise", status="completed", stage="completed",
        created_at=now, updated_at=now,
        repository_url="https://github.com/Example-Owner/exercise-repo",
        commit_sha="a" * 40,
    )
    record = module.model_dump_json()
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE modules (id TEXT PRIMARY KEY, record TEXT NOT NULL, "
            "created_at TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO modules VALUES (?, ?, ?)", (module.id, record, now.isoformat())
        )
    return module.id, record


def test_legacy_startup_backfills_repository_without_changing_module_record(tmp_path: Path) -> None:
    path = tmp_path / "modules.sqlite3"
    module_id, original_record = _legacy_database(path)

    repository = ModuleRepository(path)
    assert repository.repository_full_name(module_id) == "Example-Owner/exercise-repo"
    assert repository.find_by_repository_full_name("example-owner/EXERCISE-repo").id == module_id

    with sqlite3.connect(path) as connection:
        stored_record = connection.execute(
            "SELECT record FROM modules WHERE id=?", (module_id,)
        ).fetchone()[0]
    assert stored_record == original_record


def test_repeated_concurrent_startup_preserves_existing_repository_mapping(tmp_path: Path) -> None:
    path = tmp_path / "modules.sqlite3"
    module_id, _ = _legacy_database(path)

    with ThreadPoolExecutor(max_workers=3) as pool:
        repositories = list(pool.map(lambda _: ModuleRepository(path), range(3)))
    assert all(repository.repository_full_name(module_id) ==
               "Example-Owner/exercise-repo" for repository in repositories)

    repositories[0].save_repository_full_name(module_id, "configured/override")
    restarted = ModuleRepository(path)
    assert restarted.repository_full_name(module_id) == "configured/override"
