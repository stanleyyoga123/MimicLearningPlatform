"""Exercise the fixed verifier image with actual learner projects."""

import os
import shutil
from pathlib import Path

import pytest

from apprenticeship.features.verification.docker_verifier import DockerVerifier
from apprenticeship.features.verification.verification_report import VerificationReport


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DOCKER_TESTS") != "1",
    reason="Set RUN_DOCKER_TESTS=1 to run the built local Docker verifier image",
)

RESOURCES = Path(__file__).resolve().parents[3] / "resources" / "verification"
SCAFFOLD_REQUIREMENTS = Path(__file__).resolve().parents[3] / ".." / "scaffold" / "requirements.txt"


@pytest.fixture
def projects(tmp_path: Path) -> tuple[Path, Path]:
    reference = tmp_path / "reference"
    starter = tmp_path / "starter"
    for label, project in (("reference", reference), ("starter", starter)):
        shutil.copytree(RESOURCES / label, project)
        shutil.copytree(RESOURCES / "frozen_tests", project / "tests")
        for test_template in (project / "tests").rglob("*.py.fixture"):
            test_template.rename(test_template.with_suffix(""))
        shutil.copy2(SCAFFOLD_REQUIREMENTS, project / "requirements.txt")
        project.chmod(0o755)
        for path in project.rglob("*"):
            path.chmod(0o755 if path.is_dir() else 0o644)
    return reference, starter


def verify(reference: Path, starter: Path) -> VerificationReport:
    verifier = DockerVerifier("apprenticeship-verifier:local")
    return verifier.verify(reference, starter, verifier._test_hashes(reference))


def failed_checks(report: VerificationReport) -> set[str]:
    return {check.name for check in report.checks if not check.passed}


def test_reference_passes_and_starter_has_intended_assertion_failure(
    projects: tuple[Path, Path],
) -> None:
    reference, starter = projects

    report = verify(reference, starter)

    assert report.passed, {check.name: check.detail for check in report.checks if not check.passed}
    assert report.summary == "Starter fails the exercise while the reference passes"


def test_changed_acceptance_tests_stop_verification_before_container_execution(
    projects: tuple[Path, Path],
) -> None:
    reference, starter = projects
    frozen = DockerVerifier._test_hashes(reference)
    (starter / "tests" / "exercise" / "test_delivery.py").write_text(
        "def test_repeated_delivery_is_ignored():\n    assert True\n"
    )

    report = DockerVerifier("apprenticeship-verifier:local").verify(reference, starter, frozen)

    assert not report.passed
    assert "starter tests frozen" in failed_checks(report)
    assert len(report.checks) == 2


def test_failing_baseline_blocks_publication(projects: tuple[Path, Path]) -> None:
    reference, starter = projects
    baseline = starter / "tests" / "baseline" / "test_health.py"
    baseline.write_text(baseline.read_text() + "\ndef test_baseline_failure():\n    assert False\n")
    shutil.copy2(baseline, reference / "tests" / "baseline" / "test_health.py")

    report = verify(reference, starter)

    assert not report.passed
    assert {"reference baseline", "starter baseline"} <= failed_checks(report)


def test_unexpected_exception_is_not_accepted_as_exercise_failure(
    projects: tuple[Path, Path],
) -> None:
    reference, starter = projects
    main = starter / "app" / "main.py"
    main.write_text(main.read_text().replace(
        "    seen.add(delivery_id)\n    return True",
        "    raise RuntimeError('broken implementation')",
    ))

    report = verify(reference, starter)

    assert not report.passed
    assert "starter exercise" in failed_checks(report)


def test_different_exercise_collection_ids_are_rejected(projects: tuple[Path, Path]) -> None:
    reference, starter = projects
    for label, project in (("reference", reference), ("starter", starter)):
        main = project / "app" / "main.py"
        main.write_text(main.read_text() + f"\nCOLLECTION_ID = '{label}'\n")
        exercise = project / "tests" / "exercise" / "test_delivery.py"
        exercise.write_text(
            "import pytest\n"
            "from app.main import COLLECTION_ID, record_delivery\n\n"
            "@pytest.mark.parametrize('delivery_id', ['delivery-1'], ids=[COLLECTION_ID])\n"
            "def test_repeated_delivery_is_ignored(delivery_id):\n"
            "    seen = set()\n"
            "    assert record_delivery(delivery_id, seen) is True\n"
            "    assert record_delivery(delivery_id, seen) is False\n"
        )

    report = verify(reference, starter)

    assert not report.passed
    assert "exercise test identities" in failed_checks(report)


def test_parameter_id_with_spaces_and_missing_expected_exception_is_accepted(
    projects: tuple[Path, Path],
) -> None:
    reference, starter = projects
    exercise = (
        "import pytest\n"
        "from app.main import record_delivery\n\n"
        "@pytest.mark.parametrize('delivery_id', ['delivery-1'], ids=['duplicate delivery'])\n"
        "def test_duplicate_is_rejected(delivery_id):\n"
        "    seen = set()\n"
        "    assert record_delivery(delivery_id, seen) is True\n"
        "    with pytest.raises(ValueError, match='duplicate'):\n"
        "        if not record_delivery(delivery_id, seen):\n"
        "            raise ValueError('duplicate')\n"
    )
    for project in (reference, starter):
        (project / "tests" / "exercise" / "test_delivery.py").write_text(exercise)

    report = verify(reference, starter)

    assert report.passed, {check.name: check.detail for check in report.checks if not check.passed}
    assert report.summary == "Starter fails the exercise while the reference passes"
