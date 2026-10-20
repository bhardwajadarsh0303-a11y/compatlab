"""Unit test suite for CompatLab engine and models."""

from __future__ import annotations

import os
from pathlib import PurePosixPath, PureWindowsPath
import tempfile
import unittest

from compatlab.models import HostInfo, OSCell, Report, Status, TestResult, Tier, to_dict
from compatlab.report import from_json, to_html, to_json
from compatlab.runner import run_all
from compatlab.tests_catalog import (
    TESTS,
    TestContext,
    is_reserved_windows_name,
    make_result,
)


class TestEngine(unittest.TestCase):
    """Test suite verifying core engine integrity."""

    def test_registry_uniqueness(self) -> None:
        """Verify registry contains 12 unique test IDs."""
        ids = [t[0] for t in TESTS]
        self.assertEqual(len(ids), 12)
        self.assertEqual(len(set(ids)), 12)

    def test_reserved_windows_name(self) -> None:
        """Verify Windows reserved device names detection logic."""
        reserved_examples = ["con", "CON", "NUL.txt", "Com3", "lpt9", "aux.tar.gz", "PRN"]
        for name in reserved_examples:
            self.assertTrue(
                is_reserved_windows_name(name),
                f"Expected '{name}' to be identified as reserved Windows device name",
            )

        valid_examples = ["console", "nul_file", "data", "auxiliary.txt", "common.py", "lpt10.txt"]
        for name in valid_examples:
            self.assertFalse(
                is_reserved_windows_name(name),
                f"Expected '{name}' to NOT be identified as reserved Windows device name",
            )

    def test_purepath_simulations(self) -> None:
        """Verify pathlib pure classes behaves consistently across platforms."""
        win_p = PureWindowsPath(r"C:\a\b.txt")
        self.assertEqual(win_p.drive, "C:")
        self.assertEqual(win_p.parts, ("C:\\", "a", "b.txt"))

        posix_p = PurePosixPath("/a/b.txt")
        self.assertEqual(posix_p.drive, "")
        self.assertEqual(posix_p.parts, ("/", "a", "b.txt"))

    def test_run_all_suite(self) -> None:
        """Verify run_all runs all 12 tests without errors on host."""
        report = run_all()
        self.assertEqual(len(report.results), len(TESTS))
        self.assertEqual(report.summary["total"], 12)
        self.assertEqual(report.summary["errors"], 0)

        for res in report.results:
            self.assertEqual(len(res.cells), 3)
            os_names = {c.os_name for c in res.cells}
            self.assertEqual(os_names, {"Windows", "Linux", "macOS"})
            for c in res.cells:
                self.assertIn(c.tier, (Tier.MEASURED, Tier.SIMULATED, Tier.REFERENCE))

    def test_json_round_trip(self) -> None:
        """Verify exported JSON can be fully reconstructed via from_json."""
        report = run_all()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            to_json(report, temp_path)
            loaded_report = from_json(temp_path)
            self.assertEqual(to_dict(loaded_report), to_dict(report))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_html_export_and_escaping(self) -> None:
        """Verify HTML export escapes dangerous HTML characters and contains title."""
        fake_result = TestResult(
            id="T99",
            name="Injection Test",
            category="Security",
            status=Status.DIFFERS,
            summary="Fake summary",
            explanation="Dangerous <script>alert('xss')</script> explanation",
            host_value="Host <img src=x onerror=alert(1)>",
            host_os="Windows",
            cells=[
                OSCell("Windows", "Win <test>", Tier.MEASURED),
                OSCell("Linux", "Lin & Co", Tier.REFERENCE),
                OSCell("macOS", "Mac \"quoted\"", Tier.REFERENCE),
            ],
            confirmed=True,
            challenge_note="Note with <b>html</b> tags",
            duration_ms=1.2,
        )

        fake_host = HostInfo(
            os_name="Windows",
            os_release="11",
            os_version="10.0",
            machine="AMD64",
            python_version="3.12.0",
            python_implementation="CPython",
            filesystem_encoding="utf-8",
            preferred_encoding="cp1252",
            stdout_encoding="utf-8",
            cpu_count=8,
            timestamp_iso="2026-10-20T12:00:00Z",
        )

        fake_report = Report(
            app_version="1.0.0",
            host=fake_host,
            results=[fake_result],
            summary={"total": 1, "differs": 1, "same": 0, "errors": 0, "skipped": 0, "confirmed": 1},
        )

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tf:
            temp_path = tf.name

        try:
            to_html(fake_report, temp_path)
            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("CompatLab Report - Windows", content)
            self.assertNotIn("<script>", content)
            self.assertIn("&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;", content)
            self.assertIn("&lt;img src=x onerror=alert(1)&gt;", content)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_deliberate_failure_isolation(self) -> None:
        """Verify that a failing test function is caught, sets Status.ERROR, and doesn't crash."""
        def bad_test(ctx: TestContext) -> TestResult:
            raise RuntimeError("Deliberate simulated failure")

        from unittest.mock import patch
        patched_tests = [("T99", "Deliberate Fail", "Debug", bad_test)]

        with patch("compatlab.runner.TESTS", patched_tests):
            rep = run_all()
            self.assertEqual(len(rep.results), 1)
            self.assertEqual(rep.results[0].status, Status.ERROR)
            self.assertEqual(rep.summary["errors"], 1)
            self.assertIn("Deliberate simulated failure", rep.results[0].error or "")


if __name__ == "__main__":
    unittest.main()
