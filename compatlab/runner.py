"""Test runner and host environment introspection."""

from __future__ import annotations

import datetime
import locale
import os
import platform
import sys
import tempfile
import time
from typing import Callable

from compatlab import __version__
from compatlab.models import HostInfo, Report, Status, TestResult
from compatlab.tests_catalog import TESTS, TestContext, make_result, Tier


def normalize_os_name(raw_system: str) -> str:
    """Normalize platform.system() into Windows, Linux, macOS, or Other."""
    system_lower = raw_system.lower()
    if "windows" in system_lower:
        return "Windows"
    if "linux" in system_lower:
        return "Linux"
    if "darwin" in system_lower or "mac" in system_lower:
        return "macOS"
    return "Other"


def collect_host_info() -> HostInfo:
    """Introspect host operating system and Python runtime."""
    raw_sys = platform.system()
    norm_os = normalize_os_name(raw_sys)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return HostInfo(
        os_name=norm_os,
        os_release=platform.release(),
        os_version=platform.version(),
        machine=platform.machine(),
        python_version=platform.python_version(),
        python_implementation=platform.python_implementation(),
        filesystem_encoding=sys.getfilesystemencoding(),
        preferred_encoding=locale.getpreferredencoding(False),
        stdout_encoding=sys.stdout.encoding or "unknown",
        cpu_count=os.cpu_count(),
        timestamp_iso=now_iso,
    )


def run_all(
    on_progress: Callable[[int, int, TestResult], None] | None = None,
    only_ids: list[str] | None = None,
) -> Report:
    """Execute compatibility tests with error isolation and progress reporting."""
    host = collect_host_info()
    tests_to_run = [
        (tid, name, cat, fn)
        for (tid, name, cat, fn) in TESTS
        if only_ids is None or tid in only_ids or tid.lower() in [i.lower() for i in only_ids]
    ]

    results: list[TestResult] = []
    total = len(tests_to_run)

    # Isolated temporary directory for the entire suite run
    with tempfile.TemporaryDirectory(prefix="compatlab_run_") as temp_dir:
        ctx = TestContext(host_os=host.os_name, temp_dir=temp_dir)

        for idx, (tid, name, cat, fn) in enumerate(tests_to_run, start=1):
            t_start = time.perf_counter()
            try:
                result = fn(ctx)
            except Exception as exc:
                t_dur = (time.perf_counter() - t_start) * 1000
                result = make_result(
                    test_id=tid,
                    name=name,
                    category=cat,
                    summary=f"Test raised an unhandled exception: {exc}",
                    explanation="An error occurred while executing this test function.",
                    host_value=f"Error: {exc}",
                    host_os=host.os_name,
                    win_val="Error",
                    win_tier=Tier.MEASURED if host.os_name == "Windows" else Tier.REFERENCE,
                    linux_val="Error",
                    linux_tier=Tier.REFERENCE,
                    macos_val="Error",
                    macos_tier=Tier.REFERENCE,
                    challenge_note="Exceptions in tests are captured and reported without crashing the runner.",
                    duration_ms=t_dur,
                    error=str(exc),
                )

            results.append(result)
            if on_progress:
                on_progress(idx, total, result)

    differs_cnt = sum(1 for r in results if r.status == Status.DIFFERS)
    same_cnt = sum(1 for r in results if r.status == Status.SAME)
    errors_cnt = sum(1 for r in results if r.status == Status.ERROR)
    skipped_cnt = sum(1 for r in results if r.status == Status.SKIPPED)
    confirmed_cnt = sum(1 for r in results if r.confirmed is True)

    summary = {
        "total": len(results),
        "differs": differs_cnt,
        "same": same_cnt,
        "errors": errors_cnt,
        "skipped": skipped_cnt,
        "confirmed": confirmed_cnt,
    }

    return Report(
        app_version=__version__,
        host=host,
        results=results,
        summary=summary,
    )
