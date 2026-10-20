"""Data models and enums for CompatLab."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any


class Tier(str, Enum):
    """Evidence tier for an OS observation."""

    MEASURED = "MEASURED"
    SIMULATED = "SIMULATED"
    REFERENCE = "REFERENCE"


class Status(str, Enum):
    """Comparison outcome across OSes."""

    DIFFERS = "DIFFERS"
    SAME = "SAME"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass
class OSCell:
    """Behavior of a specific OS for a given test."""

    os_name: str  # "Windows" | "Linux" | "macOS"
    value: str  # Short human-readable behavior
    tier: Tier


@dataclass
class TestResult:
    """Outcome and metadata for a single compatibility test."""

    id: str  # e.g., "T01"
    name: str  # e.g., "Path separators"
    category: str  # Paths, Files, Permissions, Links, Text, Environment
    status: Status
    summary: str  # One-line takeaway
    explanation: str  # 2 to 4 sentences on why OSes differ
    host_value: str  # Observed on current machine
    host_os: str  # Host OS name
    cells: list[OSCell]  # Exactly 3 cells: Windows, Linux, macOS
    confirmed: bool | None  # Measured host_value matches reference expectation
    challenge_note: str  # Pitfall / developer challenge
    duration_ms: float
    error: str | None = None


@dataclass
class HostInfo:
    """Information about the current machine and Python runtime."""

    os_name: str  # Windows | Linux | macOS | Other
    os_release: str
    os_version: str
    machine: str
    python_version: str
    python_implementation: str
    filesystem_encoding: str
    preferred_encoding: str
    stdout_encoding: str
    cpu_count: int | None
    timestamp_iso: str


@dataclass
class Report:
    """Complete test suite execution report."""

    app_version: str
    host: HostInfo
    results: list[TestResult]
    summary: dict[str, int]


def to_dict(obj: Any) -> Any:
    """Recursively convert dataclasses and enums into JSON-serializable dicts."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, list):
        return [to_dict(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(to_dict(item) for item in obj)
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj
