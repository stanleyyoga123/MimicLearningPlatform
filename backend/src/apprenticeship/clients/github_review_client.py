"""Read a private PR and publish one pinned GitHub review."""

import json
import os
import re
import socket
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from pydantic import ValidationError

from apprenticeship.clients.github_app_client import GitHubAppClient
from apprenticeship.clients.github_review_models import GitHubPull, PublishedReview, ReviewSnapshot
from apprenticeship.features.submissions.submission_record import ReviewFinding


_HELPER = '!f() { printf "username=x-access-token\\npassword=%s\\n" "$APPRENTICESHIP_INSTALLATION_TOKEN"; }; f'
_HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_MAX_DIFF_BYTES = 2_000_000


class GitHubReviewClient:
    def __init__(self, app: GitHubAppClient) -> None:
        self._app = app

    def reviewer_login(self) -> str:
        return self._app.reviewer_login()

    def get_pull(self, repository: str, number: int) -> GitHubPull:
        self._validate_repository(repository)
        try:
            return GitHubPull.model_validate(
                self._request(repository, "GET", f"/repos/{repository}/pulls/{number}")
            )
        except ValidationError as error:
            raise RuntimeError("GitHub returned incomplete pull request details") from error

    def fetch_snapshot(self, repository: str, number: int, base_sha: str,
                       head_sha: str, starter_sha: str, workspace: Path) -> ReviewSnapshot:
        self._validate_repository(repository)
        workspace.mkdir(parents=True, exist_ok=True)
        git_workspace = workspace / "git"
        git_workspace.mkdir()
        self._git(git_workspace, "init", "-q")
        remote = f"https://github.com/{repository}.git"
        self._git(git_workspace, "remote", "add", "origin", remote)
        self._git(git_workspace, "fetch", "--no-tags", "origin",
                  "refs/heads/main", f"refs/pull/{number}/head", repository=repository)
        for sha in (base_sha, head_sha, starter_sha):
            self._git(git_workspace, "cat-file", "-e", f"{sha}^{{commit}}")
        self._git(git_workspace, "merge-base", "--is-ancestor", starter_sha, base_sha)
        merge_base = self._git(git_workspace, "merge-base", base_sha, head_sha).strip()
        paths = self._git(git_workspace, "diff", "--name-only", "-z", merge_base, head_sha).split("\0")
        changed_paths = frozenset(path for path in paths if path)
        if len(changed_paths) > 300 or not changed_paths:
            raise ValueError("Pull request has no changes or exceeds the 300-file review limit")
        if any(path.startswith("/") or ".." in Path(path).parts for path in changed_paths):
            raise ValueError("Pull request has unsafe file paths")
        self._reject_special_entries(git_workspace, merge_base, changed_paths)
        numstat = self._git(git_workspace, "diff", "--numstat", merge_base, head_sha)
        if any(line.startswith("-\t-\t") for line in numstat.splitlines()):
            raise ValueError("Binary pull request changes cannot be reviewed automatically")
        diff = self._git(git_workspace, "diff", "--no-ext-diff", "--unified=3", merge_base, head_sha)
        if len(diff.encode("utf-8")) > _MAX_DIFF_BYTES:
            raise ValueError("Pull request diff exceeds the 2 MB review limit")
        line_diff = self._git(git_workspace, "diff", "--no-ext-diff", "--unified=0", merge_base, head_sha)
        material = workspace / "material"
        material.mkdir()
        self._write_material(git_workspace, head_sha, material / "review_material.txt", changed_paths)
        self._write_material(git_workspace, starter_sha, material / "starter_material.txt",
                             frozenset())
        return ReviewSnapshot(material, diff, self._changed_lines(line_diff), changed_paths)

    def _write_material(self, git_workspace: Path, sha: str, destination: Path,
                        changed_paths: frozenset[str]) -> None:
        tracked = self._tree_entries(git_workspace, sha)
        total = 0
        with destination.open("w", encoding="utf-8") as output:
            for mode, path in tracked:
                if path.startswith("/") or ".." in Path(path).parts:
                    raise ValueError("Pull request has unsafe source paths")
                if mode in {"120000", "160000"}:
                    raise ValueError("Pull request uses symlinks or submodules that cannot be reviewed")
                if Path(path).name == "AGENTS.md" or path.startswith(".codex/"):
                    continue
                if not (path.startswith(("app/", "tests/")) or path in
                        {"README.md", "TASK.md", "requirements.txt"} or path in changed_paths):
                    continue
                source = self._git(git_workspace, "show", f"{sha}:{path}")
                total += len(source.encode("utf-8"))
                if total > _MAX_DIFF_BYTES:
                    raise ValueError("Pull request source exceeds the 2 MB review limit")
                output.write(f"\n<file path={json.dumps(path)}>\n{source}\n</file>\n")

    def _reject_special_entries(self, git_workspace: Path, sha: str,
                                changed_paths: frozenset[str]) -> None:
        for mode, path in self._tree_entries(git_workspace, sha):
            if path in changed_paths and mode in {"120000", "160000"}:
                raise ValueError("Pull request uses symlinks or submodules that cannot be reviewed")

    def _tree_entries(self, git_workspace: Path, sha: str) -> list[tuple[str, str]]:
        raw = self._git(git_workspace, "ls-tree", "-r", "-z", sha)
        entries = []
        for entry in filter(None, raw.split("\0")):
            metadata, separator, path = entry.partition("\t")
            if not separator or len(metadata.split(" ")) != 3 or not path:
                raise RuntimeError("Git returned an incomplete source tree")
            entries.append((metadata.split(" ", 1)[0], path))
        return entries

    def find_review(self, repository: str, number: int, marker: str,
                    head_sha: str) -> PublishedReview | None:
        self._validate_repository(repository)
        reviewer = self.reviewer_login()
        for page in range(1, 11):
            raw = self._request(repository, "GET", f"/repos/{repository}/pulls/{number}/reviews?per_page=100&page={page}")
            if not isinstance(raw, list):
                raise RuntimeError("GitHub returned an invalid review list")
            for item in raw:
                try:
                    review = PublishedReview.model_validate(item)
                except ValidationError as error:
                    raise RuntimeError("GitHub returned incomplete review details") from error
                if (marker in (review.body or "") and review.commit_id == head_sha
                        and review.user.login.lower() == reviewer.lower()):
                    return review
            if len(raw) < 100:
                return None
        raise RuntimeError("Could not fully reconcile existing GitHub reviews")

    def publish_review(self, repository: str, number: int, head_sha: str,
                       marker: str, summary: str, findings: list[ReviewFinding],
                       changed_lines: frozenset[tuple[str, int, str]]) -> PublishedReview:
        self._validate_repository(repository)
        blocking = any(finding.blocking for finding in findings)
        comments = []
        broad = []
        for finding in findings:
            if (finding.path and finding.line and finding.side and
                    (finding.path, finding.line, finding.side) in changed_lines):
                comments.append({"path": finding.path, "line": finding.line,
                                 "side": finding.side, "body": finding.body})
            else:
                location = f"{finding.path}:{finding.line}: " if finding.path else ""
                broad.append(f"- {location}{finding.body}")
        body = f"{summary.strip()}\n\n" + ("\n".join(broad) + "\n\n" if broad else "") + marker
        raw = self._request(repository, "POST", f"/repos/{repository}/pulls/{number}/reviews", {
            "commit_id": head_sha,
            "event": "REQUEST_CHANGES" if blocking else "APPROVE",
            "body": body,
            "comments": comments,
        })
        try:
            return PublishedReview.model_validate(raw)
        except ValidationError as error:
            raise RuntimeError("GitHub did not confirm the published review") from error

    @staticmethod
    def _changed_lines(diff: str) -> frozenset[tuple[str, int, str]]:
        changed: set[tuple[str, int, str]] = set()
        path = ""
        old_path = ""
        rename = False
        left = right = 0
        for line in diff.splitlines():
            if line.startswith("diff --git "):
                path = old_path = ""
                rename = False
            elif line.startswith("rename from ") or line.startswith("rename to "):
                rename = True
            elif line.startswith("--- a/"):
                old_path = line[6:]
            if line.startswith("+++ b/"):
                path = line[6:]
            elif line == "+++ /dev/null":
                path = old_path
            elif line.startswith("@@"):
                match = _HUNK.match(line)
                if match:
                    left, right = map(int, match.groups())
            elif line.startswith("+") and not line.startswith("+++"):
                if path and not rename:
                    changed.add((path, right, "RIGHT"))
                right += 1
            elif line.startswith("-") and not line.startswith("---"):
                if path and not rename:
                    changed.add((path, left, "LEFT"))
                left += 1
            elif line.startswith(" "):
                left += 1
                right += 1
        return frozenset(changed)

    @staticmethod
    def _validate_repository(repository: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Invalid GitHub repository")

    def _request(self, repository: str, method: str, path: str,
                 data: dict | None = None) -> object:
        request = urllib.request.Request(
            f"https://api.github.com{path}",
            data=json.dumps(data).encode("utf-8") if data is not None else None,
            method=method,
            headers={"Authorization": f"Bearer {self._app.token_for(repository)}",
                     "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json",
                     "X-GitHub-Api-Version": "2022-11-28"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"GitHub review request failed (HTTP {error.code})") from error
        except urllib.error.URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise RuntimeError("GitHub review request timed out; retry this submission") from error
            raise RuntimeError("GitHub review request could not connect") from error
        except (TimeoutError, socket.timeout) as error:
            raise RuntimeError("GitHub review request timed out; retry this submission") from error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise RuntimeError("GitHub returned malformed JSON; retry this submission") from error

    def _git(self, workspace: Path, *args: str, repository: str | None = None) -> str:
        allowed = {"PATH", "HOME", "USER", "TMPDIR", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR"}
        env = {key: value for key, value in os.environ.items() if key in allowed}
        env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_TERMINAL_PROMPT": "0"})
        command = ["git", "-c", "core.hooksPath=/dev/null"]
        if repository is not None:
            env["APPRENTICESHIP_INSTALLATION_TOKEN"] = self._app.token_for(repository)
            command.extend(["-c", f"credential.helper={_HELPER}"])
        command.extend(args)
        try:
            result = subprocess.run(command, cwd=workspace, env=env, capture_output=True,
                                    text=True, timeout=90)
        except (subprocess.TimeoutExpired, OSError, UnicodeError) as error:
            raise RuntimeError("Could not retrieve the complete pull request snapshot") from error
        if result.returncode:
            raise RuntimeError("Could not retrieve the complete pull request snapshot")
        return result.stdout
