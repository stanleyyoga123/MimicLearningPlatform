"""Trusted verifier program baked into the Docker image."""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from pydantic import ValidationError

from pytest_report import PytestReport


def run_health() -> dict:
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8765"],
        cwd="/tmp/work", stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    try:
        for _ in range(40):
            if server.poll() is not None:
                return {"status": "failed", "collected": 0, "failed": 0, "node_ids": [], "failed_ids": [], "detail": "Application did not start"}
            try:
                with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=1) as response:
                    if response.status == 200:
                        return {"status": "passed", "collected": 0, "failed": 0, "node_ids": [], "failed_ids": [], "detail": "GET /health returned 200"}
                    return {"status": "failed", "collected": 0, "failed": 0, "node_ids": [], "failed_ids": [], "detail": f"GET /health returned {response.status}"}
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.2)
        return {"status": "failed", "collected": 0, "failed": 0, "node_ids": [], "failed_ids": [], "detail": "Application health check timed out"}
    finally:
        server.terminate()
        try:
            server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server.kill()


def run_tests(stage: str) -> dict:
    path = f"tests/{stage}"
    if not Path("/tmp/work", path).is_dir():
        return {"status": "failed", "collected": 0, "failed": 0, "node_ids": [], "failed_ids": [], "detail": f"Missing {path}"}
    report_path = Path("/tmp/pytest-report.json")
    report_path.unlink(missing_ok=True)
    env = dict(os.environ)
    env.update({
        "APPRENTICESHIP_TEST_REPORT": str(report_path),
        "PYTHONPATH": "/verifier",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    })
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "trusted_report", "-q", "-rA", "--tb=short", path],
        cwd="/tmp/work", env=env, text=True, capture_output=True, timeout=90,
    )
    output = completed.stdout + completed.stderr
    try:
        report = PytestReport.model_validate(json.loads(report_path.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError, ValidationError):
        return {"status": "failed", "collected": 0, "failed": 0, "node_ids": [], "failed_ids": [], "detail": "Trusted pytest report missing or invalid: " + output[-600:]}
    collected = len(report.node_ids)
    failed = len(report.failed_ids)
    if collected == 0 or report.has_error or report.has_skip_or_xfail:
        status = "failed"
    elif completed.returncode == 0:
        status = "passed"
    elif completed.returncode == 1 and failed > 0 and report.failed_ids == report.assertion_failed_ids:
        status = "assertion_failed"
    else:
        status = "failed"
    failure_summary = "\n".join(f"FAILED {node_id}" for node_id in report.failed_ids)
    detail = (failure_summary + "\n" + output[-1200:]).strip()
    return {"status": status, "collected": collected, "failed": failed, "node_ids": report.node_ids, "failed_ids": report.failed_ids, "detail": detail}


def main() -> None:
    stage = sys.argv[1]
    if stage not in {"health", "baseline", "exercise"}:
        raise ValueError("Unknown verification stage")
    shutil.copytree("/input", "/tmp/work", symlinks=False)
    report = run_health() if stage == "health" else run_tests(stage)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
