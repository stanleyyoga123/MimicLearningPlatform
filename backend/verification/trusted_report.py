"""Pytest plugin baked into the verifier image for structured test outcomes."""

import json
import os
from pathlib import Path

import pytest


class TrustedReport:
    def __init__(self) -> None:
        self.node_ids: list[str] = []
        self.failed_ids: list[str] = []
        self.assertion_failed_ids: list[str] = []
        self.has_error = False
        self.has_skip_or_xfail = False

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.node_ids = [item.nodeid for item in session.items]

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.failed:
            self.has_error = True
        if report.skipped:
            self.has_skip_or_xfail = True

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: pytest.Item, call: pytest.CallInfo):
        outcome = yield
        report = outcome.get_result()
        if report.skipped or hasattr(report, "wasxfail"):
            self.has_skip_or_xfail = True
        if not report.failed:
            return
        if report.when != "call":
            self.has_error = True
            return
        self.failed_ids.append(item.nodeid)
        if call.excinfo and isinstance(call.excinfo.value, (AssertionError, pytest.fail.Exception)):
            self.assertion_failed_ids.append(item.nodeid)
        else:
            self.has_error = True

    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        report = {
            "node_ids": self.node_ids,
            "failed_ids": self.failed_ids,
            "assertion_failed_ids": self.assertion_failed_ids,
            "has_error": self.has_error,
            "has_skip_or_xfail": self.has_skip_or_xfail,
        }
        Path(os.environ["APPRENTICESHIP_TEST_REPORT"]).write_text(json.dumps(report), encoding="utf-8")


def pytest_configure(config: pytest.Config) -> None:
    config.pluginmanager.register(TrustedReport(), name="apprenticeship-trusted-report")
