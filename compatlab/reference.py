"""Built-in reference knowledge base for cross-platform OS behaviors."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class OSExpectation:
    expected_value: str
    source_note: str


REFERENCE_DATA: dict[str, dict[str, OSExpectation]] = {
    "T01": {
        "Windows": OSExpectation(
            "\\ (also accepts /)",
            "Microsoft Docs: Naming Files, Paths, and Namespaces",
        ),
        "Linux": OSExpectation(
            "/",
            "POSIX.1-2017 Base Definitions",
        ),
        "macOS": OSExpectation(
            "/",
            "Apple File System Guide",
        ),
    },
    "T02": {
        "Windows": OSExpectation(
            "Drive letters and UNC",
            "Microsoft Docs: Naming Files, Paths, and Namespaces",
        ),
        "Linux": OSExpectation(
            "Single root /",
            "POSIX.1 Pathname Resolution",
        ),
        "macOS": OSExpectation(
            "Single root /",
            "Apple Developer Documentation",
        ),
    },
    "T03": {
        "Windows": OSExpectation(
            "~260 chars legacy limit unless long paths enabled",
            "Microsoft Docs: Maximum Path Length Limitation",
        ),
        "Linux": OSExpectation(
            "~4096 total (PATH_MAX)",
            "Linux limits.h (PATH_MAX)",
        ),
        "macOS": OSExpectation(
            "~1024 (PATH_MAX)",
            "macOS sys/syslimits.h",
        ),
    },
    "T04": {
        "Windows": OSExpectation(
            "Case-insensitive, case-preserving",
            "Windows NTFS / FAT32 Specification",
        ),
        "Linux": OSExpectation(
            "Case-sensitive",
            "Linux VFS Architecture",
        ),
        "macOS": OSExpectation(
            "Case-insensitive by default (APFS), configurable",
            "Apple APFS Specification",
        ),
    },
    "T05": {
        "Windows": OSExpectation(
            "Many characters and names forbidden",
            "Microsoft Docs: Naming Files, Paths, and Namespaces",
        ),
        "Linux": OSExpectation(
            "Only / and NUL byte forbidden",
            "POSIX.1 Filename Rules",
        ),
        "macOS": OSExpectation(
            "Only / (and : shown as / in Finder)",
            "Apple HFS+/APFS Guidelines",
        ),
    },
    "T06": {
        "Windows": OSExpectation(
            "CRLF (\\r\\n)",
            "DOS / Windows Text Mode Conventions",
        ),
        "Linux": OSExpectation(
            "LF (\\n)",
            "POSIX General Terminal Interface",
        ),
        "macOS": OSExpectation(
            "LF (\\n)",
            "macOS UNIX Standard (since OS X)",
        ),
    },
    "T07": {
        "Windows": OSExpectation(
            "Preserves what you give it (NFC typical)",
            "Microsoft Unicode Filename Storage",
        ),
        "Linux": OSExpectation(
            "Preserves bytes",
            "Linux Kernel Byte String Filenames",
        ),
        "macOS": OSExpectation(
            "Normalizes to NFD on HFS+, preserves on APFS",
            "Apple File System Guide: Unicode Normalization",
        ),
    },
    "T08": {
        "Windows": OSExpectation(
            "chmod only toggles the read-only flag, mode bits are synthetic",
            "Python stat / msvcrt runtime documentation",
        ),
        "Linux": OSExpectation(
            "Full POSIX rwx bits for user/group/other",
            "POSIX.1 Permissions & mode_t",
        ),
        "macOS": OSExpectation(
            "Full POSIX rwx bits (BSD heritage)",
            "BSD / macOS chmod(2) manpage",
        ),
    },
    "T09": {
        "Windows": OSExpectation(
            "Executability depends on file extension (PATHEXT)",
            "Windows CMD/PowerShell Execution Architecture",
        ),
        "Linux": OSExpectation(
            "Depends on the execute permission bit",
            "Linux execve(2) and POSIX x-bit",
        ),
        "macOS": OSExpectation(
            "Depends on the execute permission bit",
            "macOS POSIX Architecture",
        ),
    },
    "T10": {
        "Windows": OSExpectation(
            "Needs Developer Mode or admin",
            "Microsoft Docs: CreateSymbolicLinkW Security Requirements",
        ),
        "Linux": OSExpectation(
            "Works for any user",
            "POSIX symlink(2)",
        ),
        "macOS": OSExpectation(
            "Works for any user",
            "macOS symlink(2)",
        ),
    },
    "T11": {
        "Windows": OSExpectation(
            "Often a legacy code page like cp1252",
            "Microsoft Windows Code Pages / ACP",
        ),
        "Linux": OSExpectation(
            "UTF-8",
            "Linux UTF-8 Locale Standards",
        ),
        "macOS": OSExpectation(
            "UTF-8",
            "macOS UTF-8 Default Locale",
        ),
    },
    "T12": {
        "Windows": OSExpectation(
            "USERPROFILE, COMSPEC, cmd/PowerShell, dir, cls",
            "Windows Environment Variables & Shell Specifications",
        ),
        "Linux": OSExpectation(
            "HOME, SHELL, bash/zsh, ls, clear",
            "POSIX Environment & Shell Standards",
        ),
        "macOS": OSExpectation(
            "HOME, SHELL (zsh default), ls, clear",
            "macOS User Environment & Zsh Defaults",
        ),
    },
}


def get_reference_value(test_id: str, os_name: str) -> str:
    """Retrieve expected reference value for a test and OS."""
    data = REFERENCE_DATA.get(test_id, {})
    item = data.get(os_name)
    return item.expected_value if item else "Unknown"


def get_reference_source(test_id: str, os_name: str) -> str:
    """Retrieve source documentation note for a test and OS."""
    data = REFERENCE_DATA.get(test_id, {})
    item = data.get(os_name)
    return item.source_note if item else "Documentation"
