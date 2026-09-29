"""Run learner and reference checks in the fixed offline verifier image."""

import hashlib
import json
import subprocess
import uuid
from pathlib import Path

from pydantic import ValidationError

from apprenticeship.features.verification.harness_result import HarnessResult
from apprenticeship.features.verification.verification_report import VerificationCheck, VerificationReport


class DockerVerifier:
    def __init__(self, image: str, timeout_seconds: int = 120) -> None:
        self._image = image
        self._timeout_seconds = timeout_seconds

    def verify(self, reference: Path, starter: Path, frozen_tests: dict[str, str]) -> VerificationReport:
        checks: list[VerificationCheck] = []
        for label, project in (("reference", reference), ("starter", starter)):
            actual = self._test_hashes(project)
            expected = frozen_tests
            checks.append(VerificationCheck(
                name=f"{label} tests frozen", passed=actual == expected and bool(expected),
                detail="Test tree matches frozen manifest" if actual == expected and expected else "Test tree changed or is empty",
            ))
        if not all(check.passed for check in checks):
            return VerificationReport(passed=False, summary="Acceptance tests changed during generation", checks=checks)
        results: dict[str, dict[str, HarnessResult]] = {}
        for label, project in (("reference", reference), ("starter", starter)):
            results[label] = {}
            for stage in ("health", "baseline", "exercise"):
                result = self._run(project, stage)
                results[label][stage] = result
                passed = self._stage_passed(label, stage, result)
                checks.append(VerificationCheck(name=f"{label} {stage}", passed=passed, detail=result.detail))
        reference_nodes = results["reference"]["exercise"].node_ids
        starter_nodes = results["starter"]["exercise"].node_ids
        nodes_match = bool(reference_nodes) and reference_nodes == starter_nodes
        checks.append(VerificationCheck(
            name="exercise test identities", passed=nodes_match,
            detail="Reference and starter collect the same exercise tests" if nodes_match else "Exercise test identities differ",
        ))
        passed = all(check.passed for check in checks)
        return VerificationReport(
            passed=passed,
            summary="Starter fails the exercise while the reference passes" if passed else "Project verification failed",
            checks=checks,
        )

    @staticmethod
    def _test_hashes(project: Path) -> dict[str, str]:
        tests = project / "tests"
        if not tests.is_dir() or tests.is_symlink():
            return {}
        hashes = {}
        for path in tests.rglob("*"):
            if path.is_symlink():
                return {}
            if path.is_file():
                hashes[path.relative_to(tests).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        return hashes

    @staticmethod
    def _stage_passed(label: str, stage: str, result: HarnessResult) -> bool:
        if stage == "health":
            return result.status == "passed"
        if stage == "baseline" or label == "reference":
            return result.status == "passed" and result.collected > 0 and len(result.node_ids) == result.collected
        return (
            result.status == "assertion_failed" and result.collected > 0
            and len(result.node_ids) == result.collected and result.failed > 0
            and result.failed == len(result.failed_ids)
            and set(result.failed_ids).issubset(result.node_ids)
        )

    def _run(self, project: Path, stage: str) -> HarnessResult:
        container_name = f"apprenticeship-verify-{uuid.uuid4().hex}"
        command = [
            "docker", "run", "--rm", "--name", container_name, "--network", "none", "--read-only",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", "128", "--memory", "512m", "--cpus", "1",
            "--user", "65532:65532", "--tmpfs", "/tmp:rw,noexec,nosuid,size=128m,uid=65532,gid=65532",
            "--mount", f"type=bind,src={project.resolve()},dst=/input,readonly",
            self._image, "python", "/harness.py", stage,
        ]
        try:
            process = subprocess.run(command, text=True, capture_output=True, timeout=self._timeout_seconds)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, timeout=15)
            return self._error("timeout", "Verification timed out")
        except FileNotFoundError:
            return self._error("unavailable", "Docker is not installed")
        if process.returncode:
            return self._error("container_error", process.stderr[-500:] or "Verifier container failed")
        try:
            return HarnessResult.model_validate(json.loads(process.stdout))
        except (json.JSONDecodeError, ValidationError):
            return self._error("invalid_report", "Verifier returned invalid JSON")

    @staticmethod
    def _error(status: str, detail: str) -> HarnessResult:
        return HarnessResult(status=status, collected=0, failed=0, node_ids=[], failed_ids=[], detail=detail)
