"""Create a completed module with distinct public, private, and learner artifacts."""

import json
from pathlib import Path

from apprenticeship.features.modules.module_repository import ModuleRepository
from apprenticeship.features.modules.module_spec import ModuleSpec
from apprenticeship.features.modules.peer_private import PeerPrivate
from apprenticeship.features.modules.peer_public import PeerPublic


def published_module(data_dir: Path) -> str:
    repository = ModuleRepository(data_dir / "modules.sqlite3")
    module = repository.create("webhook-module")
    module.status = "completed"
    module.stage = "completed"
    module.repository_url = "https://github.com/learner/webhook-module"
    module.spec = ModuleSpec(
        title="Duplicate webhook orders",
        scenario="A retry of one delivery creates a second order in the service.",
        learning_objective="Implement idempotent delivery handling",
        task_type="bugfix",
        task_brief="Prevent repeated webhook deliveries from creating duplicate orders.",
        expected_behavior="A repeated delivery returns the original order without creating another.",
        acceptance_criteria=["One order is created per delivery ID."],
        simplifications=[],
    )
    peers = [
        PeerPrivate(
            name="Avery", role="Backend engineer", contribution_history="Implemented delivery routes",
            responsibilities=["Delivery endpoint"], owned_files=["app/main.py"],
            known_facts=["backend-only-fact-481"], unknown_topics=["QA fixtures"],
            response_boundaries=["Speak only about routes"],
        ),
        PeerPrivate(
            name="Blair", role="QA engineer", contribution_history="Built replay tests",
            responsibilities=["Replay fixtures"], owned_files=["tests/exercise/test_replay.py"],
            known_facts=["qa-only-fact-729"], unknown_topics=["Endpoint internals"],
            response_boundaries=["Speak only about tests"],
        ),
    ]
    private_fields = {"known_facts", "unknown_topics", "response_boundaries"}
    module.peers = [PeerPublic.model_validate(peer.model_dump(exclude=private_fields)) for peer in peers]
    repository.save(module)

    root = data_dir / "modules" / module.id
    private = root / "private"
    starter = root / "starter"
    (starter / "app").mkdir(parents=True)
    (starter / "tests" / "exercise").mkdir(parents=True)
    private.mkdir()
    (root / "reference").mkdir()
    (starter / "app" / "main.py").write_text("# starter-route-marker-184\n")
    (starter / "tests" / "exercise" / "test_replay.py").write_text("# qa-fixture-marker-531\n")
    (starter / "TASK.md").write_text("Fix duplicate webhook deliveries.\n")
    (starter / "README.md").write_text("Run tests to inspect behavior.\n")
    (private / "peers.json").write_text(json.dumps([peer.model_dump() for peer in peers]))
    (private / "source.txt").write_text("private-source-marker-914")
    (private / "codex.log").write_text("private-log-marker-642")
    (root / "reference" / "solution.py").write_text("private-reference-marker-377")
    return module.id
