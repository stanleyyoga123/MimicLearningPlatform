"""Reference and starter verification gates."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from apprenticeship.features.verification.docker_verifier import DockerVerifier
from apprenticeship.features.verification.harness_result import HarnessResult


def test_verifier_accepts_reference_pass_and_starter_assertion_failure(tmp_path: Path) -> None:
    reference = tmp_path / "reference"
    starter = tmp_path / "starter"
    for project in (reference, starter):
        (project / "tests" / "exercise").mkdir(parents=True)
        (project / "tests" / "exercise" / "test_task.py").write_text("def test_task(): assert True")
    frozen = {"exercise/test_task.py": hashlib.sha256(b"def test_task(): assert True").hexdigest()}
    verifier = DockerVerifier("test")
    verifier._run = lambda project, stage: HarnessResult(
        status="assertion_failed" if project == starter and stage == "exercise" else "passed",
        collected=0 if stage == "health" else 1,
        failed=1 if project == starter and stage == "exercise" else 0,
        node_ids=[] if stage == "health" else [f"tests/{stage}/test_task.py::test_task"],
        failed_ids=["tests/exercise/test_task.py::test_task"] if project == starter and stage == "exercise" else [],
        detail=stage,
    )

    report = verifier.verify(reference, starter, frozen)

    assert report.passed
    assert len(report.checks) == 9


def test_verifier_stops_when_frozen_tests_change(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / "tests").mkdir(parents=True)
    (project / "tests" / "test_task.py").write_text("changed")
    verifier = DockerVerifier("test")

    report = verifier.verify(project, project, {"test_task.py": "old-sha"})

    assert not report.passed
    assert report.summary == "Acceptance tests changed during generation"


def test_trusted_report_preserves_whitespace_ids_and_classifies_pytest_fail(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_task.py").write_text(
        "import pytest\n"
        "@pytest.mark.parametrize('value', ['space value', 'tab\\tvalue'])\n"
        "def test_missing_expected_error(value):\n"
        "    with pytest.raises(ValueError):\n"
        "        pass\n"
    )
    report_path = tmp_path / "report.json"
    verification = Path(__file__).resolve().parents[4] / "verification"
    env = dict(os.environ, PYTHONPATH=str(verification), APPRENTICESHIP_TEST_REPORT=str(report_path))

    process = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "trusted_report", "-q", "tests"],
        cwd=tmp_path, env=env, capture_output=True, text=True,
    )
    report = json.loads(report_path.read_text())

    assert process.returncode == 1
    assert len(report["node_ids"]) == 2
    assert any("space value" in node_id for node_id in report["node_ids"])
    assert report["failed_ids"] == report["assertion_failed_ids"]
    assert not report["has_error"]


def test_trusted_report_rejects_runtime_error(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_task.py").write_text("def test_runtime():\n    raise RuntimeError('bad')\n")
    report_path = tmp_path / "report.json"
    verification = Path(__file__).resolve().parents[4] / "verification"
    env = dict(os.environ, PYTHONPATH=str(verification), APPRENTICESHIP_TEST_REPORT=str(report_path))

    process = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "trusted_report", "-q", "tests"],
        cwd=tmp_path, env=env, capture_output=True, text=True,
    )
    report = json.loads(report_path.read_text())

    assert process.returncode == 1
    assert report["failed_ids"] == ["tests/test_task.py::test_runtime"]
    assert report["assertion_failed_ids"] == []
    assert report["has_error"]


def test_pytest_report_rejects_malformed_boolean_and_node_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    verification = Path(__file__).resolve().parents[4] / "verification"
    monkeypatch.syspath_prepend(str(verification))
    from pytest_report import PytestReport

    with pytest.raises(ValidationError):
        PytestReport.model_validate({
            "node_ids": "tests/test_task.py::test_task",
            "failed_ids": [],
            "assertion_failed_ids": [],
            "has_error": "false",
            "has_skip_or_xfail": False,
        })
