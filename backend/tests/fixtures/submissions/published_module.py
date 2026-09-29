from pathlib import Path

from apprenticeship.features.modules.module_repository import ModuleRepository
from tests.fixtures.learner_workspace.published_module import published_module


def reviewable_module(data_dir: Path) -> str:
    module_id = published_module(data_dir)
    repository = ModuleRepository(data_dir / "modules.sqlite3")
    module = repository.get(module_id)
    assert module is not None
    module.commit_sha = "a" * 40
    repository.save(module)
    repository.save_repository_full_name(module_id, "learner/webhook-module")
    return module_id
