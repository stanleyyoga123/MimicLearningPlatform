"""Publishing keeps private artifacts out of the learner export."""

from pathlib import Path

import pytest

from apprenticeship.clients.github_publisher import GitHubPublisher


def test_export_contains_only_learner_artifacts(tmp_path: Path) -> None:
    starter = tmp_path / "starter"
    export = tmp_path / "export"
    (starter / "app").mkdir(parents=True)
    (starter / "tests").mkdir()
    (starter / "reference").mkdir()
    (starter / "app" / "main.py").write_text("app = True")
    (starter / "tests" / "test_main.py").write_text("def test_example(): assert True")
    (starter / "README.md").write_text("Run the exercise")
    (starter / "requirements.txt").write_bytes(
        (Path(__file__).resolve().parents[3] / "scaffold" / "requirements.txt").read_bytes()
    )
    (starter / "reference" / "solution.py").write_text("private")
    (starter / "source.pdf").write_text("private")
    export.mkdir()

    GitHubPublisher._export(starter, export)

    assert (export / "app" / "main.py").exists()
    assert (export / "tests" / "test_main.py").exists()
    assert not (export / "reference").exists()
    assert not (export / "source.pdf").exists()


def test_export_rejects_symlink_in_learner_tree(tmp_path: Path) -> None:
    starter = tmp_path / "starter"
    export = tmp_path / "export"
    (starter / "app").mkdir(parents=True)
    (starter / "tests").mkdir()
    (starter / "README.md").write_text("Run")
    (starter / "requirements.txt").write_bytes(
        (Path(__file__).resolve().parents[3] / "scaffold" / "requirements.txt").read_bytes()
    )
    (starter / "app" / "private.py").symlink_to(tmp_path / "secret")
    export.mkdir()

    with pytest.raises(ValueError, match="Symlink"):
        GitHubPublisher._export(starter, export)


def test_export_rejects_hidden_runtime_file(tmp_path: Path) -> None:
    starter = tmp_path / "starter"
    export = tmp_path / "export"
    (starter / "app").mkdir(parents=True)
    (starter / "tests").mkdir()
    (starter / "README.md").write_text("Run")
    (starter / "requirements.txt").write_bytes(
        (Path(__file__).resolve().parents[3] / "scaffold" / "requirements.txt").read_bytes()
    )
    (starter / "app" / ".env").write_text("PRIVATE=true")
    export.mkdir()

    with pytest.raises(ValueError, match="Hidden|Unsupported"):
        GitHubPublisher._export(starter, export)


def test_existing_repository_must_match_private_marker() -> None:
    publisher = GitHubPublisher("test-token")
    publisher._request = lambda method, path, data=None: {
        "full_name": "user/target", "private": False,
        "description": "apprenticeship-module:123",
        "html_url": "https://github.com/user/target",
    }

    with pytest.raises(RuntimeError, match="privacy"):
        publisher._ensure_repository("user/target", "target", "123")


def test_force_add_stages_reviewed_files_even_if_gitignore_excludes_them(tmp_path: Path) -> None:
    starter = tmp_path / "starter"
    export = tmp_path / "export"
    (starter / "app").mkdir(parents=True)
    (starter / "tests").mkdir()
    (starter / "app" / "main.py").write_text("app = True")
    (starter / "tests" / "test_main.py").write_text("def test_example(): assert True")
    (starter / "README.md").write_text("Run")
    (starter / ".gitignore").write_text("app/\n")
    (starter / "requirements.txt").write_bytes(
        (Path(__file__).resolve().parents[3] / "scaffold" / "requirements.txt").read_bytes()
    )
    export.mkdir()

    GitHubPublisher._export(starter, export)
    GitHubPublisher._git(export, "init", "-b", "main")
    GitHubPublisher._git(export, "add", "--force", "--all")

    assert "app/main.py" in GitHubPublisher._git(export, "ls-files").splitlines()
