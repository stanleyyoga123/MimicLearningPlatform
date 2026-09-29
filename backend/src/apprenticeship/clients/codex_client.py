"""Isolated noninteractive Codex invocation."""

import json
import os
import signal
import subprocess
import threading
from pathlib import Path
from typing import Callable, Literal


class CodexClient:
    def __init__(self, binary: str, model: str | None, timeout_seconds: int = 600) -> None:
        self._binary = binary
        self._model = model
        self._timeout_seconds = timeout_seconds

    def generate(
        self,
        prompt: str,
        workspace: Path,
        output_schema: dict,
        output_path: Path,
        event_callback: Callable[[str], None] | None = None,
    ) -> dict:
        return self._execute(prompt, workspace, output_schema, output_path, event_callback, "workspace-write")

    def review(
        self,
        prompt: str,
        workspace: Path,
        output_schema: dict,
        output_path: Path,
        event_callback: Callable[[str], None] | None = None,
    ) -> dict:
        return self._execute(prompt, workspace, output_schema, output_path, event_callback, "read-only")

    def _execute(
        self,
        prompt: str,
        workspace: Path,
        output_schema: dict,
        output_path: Path,
        event_callback: Callable[[str], None] | None,
        sandbox: Literal["workspace-write", "read-only"],
    ) -> dict:
        workspace = workspace.resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        output_path = output_path.resolve()
        if not output_path.is_relative_to(workspace):
            raise ValueError("Codex output must stay inside its workspace")
        schema_path = workspace / ".codex-output-schema.json"
        schema_path.write_text(json.dumps(output_schema), encoding="utf-8")
        args = [
            self._binary, "exec", "--json", "--sandbox", sandbox,
            "--skip-git-repo-check", "--ephemeral", "--ignore-user-config", "--ignore-rules",
            "-c", 'approval_policy="never"', "--output-schema", str(schema_path),
            "-o", str(output_path), "-C", str(workspace),
        ]
        if self._model:
            args.extend(["--model", self._model])
        args.append("-")
        output_path.unlink(missing_ok=True)
        allowed = {"PATH", "HOME", "USER", "TMPDIR", "CODEX_HOME", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR"}
        env = {key: value for key, value in os.environ.items() if key in allowed}
        process = subprocess.Popen(
            args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=workspace, env=env, start_new_session=True,
        )
        timed_out = threading.Event()

        def stop_process() -> None:
            timed_out.set()
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)

        timer = threading.Timer(self._timeout_seconds, stop_process)
        timer.start()
        stderr_chunks: list[str] = []

        def read_stderr() -> None:
            assert process.stderr is not None
            stderr_chunks.append(process.stderr.read())

        stderr_reader = threading.Thread(target=read_stderr, daemon=True)
        stderr_reader.start()
        try:
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write(prompt)
            process.stdin.close()
            for line in process.stdout:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event_type = event.get("type")
                if event_callback and event_type in {"turn.started", "turn.completed", "turn.failed", "item.started", "item.completed"}:
                    event_callback(event_type)
            process.wait()
        finally:
            timer.cancel()
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            stderr_reader.join(timeout=1)
        if timed_out.is_set():
            raise TimeoutError("Codex invocation timed out")
        if process.returncode != 0:
            detail = "Check saved Codex authentication and the configured model"
            raise RuntimeError(f"Codex invocation failed (exit {process.returncode}). {detail}")
        if not output_path.is_file():
            raise RuntimeError("Codex did not write structured output")
        try:
            response = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Codex returned invalid JSON") from exc
        if not isinstance(response, dict):
            raise RuntimeError("Codex response must be an object")
        return response
