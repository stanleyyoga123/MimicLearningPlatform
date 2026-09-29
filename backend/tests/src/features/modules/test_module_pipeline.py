import json
import shutil
from pathlib import Path

import pytest

from apprenticeship.clients.publication import Publication
from apprenticeship.features.modules.module_pipeline import (
    ModulePipeline, assert_frozen_tests, hash_tests, learner_hashes, purge_generated_caches,
)
from apprenticeship.features.modules.module_repository import ModuleRepository
from apprenticeship.features.verification.verification_report import VerificationCheck, VerificationReport


SPEC = {
    "title": "Duplicate webhook orders",
    "scenario": "A webhook may be delivered twice and create duplicate orders.",
    "learning_objective": "Implement idempotency",
    "task_type": "bugfix",
    "task_brief": "Fix duplicate order creation on repeated deliveries.",
    "expected_behavior": "Repeated deliveries return the same persisted order.",
    "acceptance_criteria": ["Two deliveries create one order"],
    "simplifications": ["Payment processing is simulated"],
}


class FakeCodex:
    def generate(self, prompt, workspace, output_schema, output_path, event_callback=None):
        if "Create ONE" in prompt:
            result = SPEC
        elif "COMPLETE, WORKING" in prompt:
            (workspace / "tests" / "exercise" / "orders").mkdir(parents=True)
            (workspace / "tests" / "exercise" / "orders" / "test_order.py").write_text(
                "def test_order_idempotency():\n    assert True\n"
            )
            result = {"summary": "Created reference"}
        elif "UNSOLVED learner" in prompt:
            (workspace / "app" / "main.py").write_text(
                "from fastapi import FastAPI\napp = FastAPI()\n"
                "@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n"
            )
            result = {"summary": "Created starter"}
        else:
            result = {"peers": [
                {
                    "name": "Alex", "role": "Backend teammate", "contribution_history": "Built service endpoints",
                    "responsibilities": ["Order endpoint"], "owned_files": ["app/main.py"],
                    "known_facts": ["Webhook route exists"], "unknown_topics": ["QA fixtures"],
                    "response_boundaries": ["No solution code"],
                },
                {
                    "name": "Sam", "role": "QA teammate", "contribution_history": "Created test fixtures",
                    "responsibilities": ["Reproduction steps"], "owned_files": ["tests/exercise/orders/test_order.py"],
                    "known_facts": ["Repeated events are expected"], "unknown_topics": ["Service internals"],
                    "response_boundaries": ["No implementation hints"],
                },
            ]}
        output_path.write_text(json.dumps(result))
        return result


class FakeVerifier:
    def verify(self, reference, starter, frozen_tests):
        assert hash_tests(reference) == frozen_tests
        assert hash_tests(starter) == frozen_tests
        return VerificationReport(
            passed=True, summary="Reference green, starter red",
            checks=[VerificationCheck(name="exercise", passed=True, detail="Expected outcomes")],
        )


class FakePublisher:
    def __init__(self):
        self.calls = 0

    def publish(self, starter, module_id, title, existing_full_name, on_repository_created):
        self.calls += 1
        on_repository_created(f"owner/{module_id}")
        return Publication(f"owner/{module_id}", f"https://github.com/owner/{module_id}", "abc123")


def test_pipeline_creates_public_starter_and_private_peer_knowledge(tmp_path: Path) -> None:
    repository = ModuleRepository(tmp_path / "modules.sqlite3")
    module = repository.create()
    private = tmp_path / "modules" / module.id / "private"
    private.mkdir(parents=True)
    (private / "source.txt").write_text("Duplicate webhook orders on replay")
    scaffold = Path(__file__).resolve().parents[4] / "scaffold"
    publisher = FakePublisher()
    pipeline = ModulePipeline(repository, tmp_path, scaffold, FakeCodex(), FakeVerifier(), publisher)

    completed = pipeline.run(module)

    starter = tmp_path / "modules" / module.id / "starter"
    assert completed.status == "completed"
    assert completed.repository_url == f"https://github.com/owner/{module.id}"
    assert len(completed.peers) == 2
    assert "known_facts" not in (starter / "PEERS.md").read_text()
    assert len(json.loads((private / "peers.json").read_text())) == 2
    assert publisher.calls == 1


def test_frozen_test_tree_rejects_changes(tmp_path: Path) -> None:
    tests = tmp_path / "tests" / "exercise"
    tests.mkdir(parents=True)
    test_file = tests / "test_order.py"
    test_file.write_text("def test_order(): assert True")
    frozen = hash_tests(tmp_path)
    test_file.write_text("def test_order(): assert False")
    with pytest.raises(ValueError, match="Acceptance tests changed"):
        assert_frozen_tests(tmp_path, frozen)


def test_publication_retry_rejects_starter_changed_after_verification(tmp_path: Path) -> None:
    repository = ModuleRepository(tmp_path / "modules.sqlite3")
    module = repository.create()
    root = tmp_path / "modules" / module.id
    private = root / "private"
    private.mkdir(parents=True)
    scaffold = Path(__file__).resolve().parents[4] / "scaffold"
    starter = root / "starter"
    shutil.copytree(scaffold, starter)
    (private / "starter_manifest.json").write_text(json.dumps(learner_hashes(starter)))
    report = VerificationReport(passed=True, summary="Verified", checks=[])
    (private / "verification.json").write_text(report.model_dump_json())
    module.stage = "publishing"
    module.status = "running"
    repository.save(module)
    (starter / "app" / "main.py").write_text("raise RuntimeError('changed')")
    publisher = FakePublisher()
    pipeline = ModulePipeline(repository, tmp_path, scaffold, FakeCodex(), FakeVerifier(), publisher)

    with pytest.raises(ValueError, match="Starter changed after verification"):
        pipeline.run(module)
    assert publisher.calls == 0


@pytest.mark.parametrize("name", [".config.json", "server.log", "main.pyc"])
def test_generated_hidden_or_runtime_artifact_is_rejected(tmp_path: Path, name: str) -> None:
    scaffold = Path(__file__).resolve().parents[4] / "scaffold"
    shutil.copytree(scaffold, tmp_path / "starter")
    artifact = tmp_path / "starter" / "app" / name
    artifact.write_text("unpublished content")

    with pytest.raises(ValueError, match="generated artifact|runtime artifact"):
        learner_hashes(tmp_path / "starter")


def test_generated_caches_are_removed_before_freezing_tests(tmp_path: Path) -> None:
    scaffold = Path(__file__).resolve().parents[4] / "scaffold"
    shutil.copytree(scaffold, tmp_path / "starter")
    cache = tmp_path / "starter" / "tests" / "baseline" / "__pycache__"
    cache.mkdir()
    (cache / "test_health.pyc").write_bytes(b"runtime cache")

    purge_generated_caches(tmp_path / "starter")

    assert not cache.exists()
    assert "baseline/test_health.py" in hash_tests(tmp_path / "starter")
