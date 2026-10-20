"""Challenges faced during cross-platform OS compatibility engineering."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ChallengeItem:
    id: int
    title: str
    what_happened: str
    how_handled: str
    affected_os: str


CHALLENGES: list[ChallengeItem] = [
    ChallengeItem(
        id=1,
        title="Hardcoded path separators break portability",
        what_happened="Hardcoding '\\' in paths causes FileNotFoundError on Linux and macOS, while '/' can occasionally fail in legacy Windows CMD commands.",
        how_handled="Used pathlib.Path and os.path.join everywhere. Path separators are normalized automatically across all operating systems.",
        affected_os="Windows, Linux, macOS",
    ),
    ChallengeItem(
        id=2,
        title="Case sensitivity surprises across filesystems",
        what_happened="Code developed on case-insensitive Windows/macOS imports 'module.py' as 'Module.py' without error, but immediately crashes on case-sensitive Linux filesystems.",
        how_handled="Maintained strict lowercase naming conventions across all files and added T04 to measure filesystem case behavior directly.",
        affected_os="Windows vs Linux / macOS",
    ),
    ChallengeItem(
        id=3,
        title="Line endings (CRLF vs LF) breaking scripts and diffs",
        what_happened="Git checkouts on Windows often convert LF to CRLF (\\r\\n). Shell scripts executed on Linux fail with '/bin/bash^M: bad interpreter', and git status shows noisy diffs.",
        how_handled="Specified .gitattributes (* text=auto, *.bat text eol=crlf) and always used explicit newline/encoding parameters when opening text files.",
        affected_os="Windows, Linux, macOS",
    ),
    ChallengeItem(
        id=4,
        title="Symlinks require administrative privileges on Windows",
        what_happened="Calling os.symlink on Windows fails with WinError 1314 (A required privilege is not held by the client) unless Developer Mode is enabled or running as Administrator.",
        how_handled="Wrapped symlink creation in try/except (OSError, NotImplementedError), returning a graceful diagnostic message rather than terminating the test suite.",
        affected_os="Windows",
    ),
    ChallengeItem(
        id=5,
        title="Reserved and illegal device names in filenames",
        what_happened="Files named 'aux.py', 'con.txt', or containing characters like ':' and '?' are valid on Linux but strictly prohibited by the Windows kernel, corrupting repositories.",
        how_handled="Implemented is_reserved_windows_name() as a pure algorithmic string validator without touching the filesystem, completely preventing console hijacking or filesystem errors.",
        affected_os="Windows vs Linux / macOS",
    ),
    ChallengeItem(
        id=6,
        title="Default text encodings differ by locale and OS",
        what_happened="Windows historically defaults to legacy ANSI code pages (such as cp1252), causing open() without encoding='utf-8' to fail or corrupt non-ASCII characters.",
        how_handled="Enforced encoding='utf-8' on every file open, configured sys.stdout.reconfigure(errors='replace') in CLI mode, and added T11 to measure runtime encodings.",
        affected_os="Windows vs Linux / macOS",
    ),
    ChallengeItem(
        id=7,
        title="Permission models are fundamentally divergent (NTFS ACLs vs POSIX bits)",
        what_happened="Calling os.chmod(path, 0o700) on Windows does not restrict read access for other users because Windows maps chmod solely to the file's read-only attribute.",
        how_handled="Documented the difference in T08, avoided reliance on POSIX mode bits for Windows security, and used synthetic mode bit reporting.",
        affected_os="Windows vs Linux / macOS",
    ),
    ChallengeItem(
        id=8,
        title="GUI differences: High-DPI scaling, fonts, and missing Tkinter",
        what_happened="Tkinter UIs can appear blurry on High-DPI Windows displays, native fonts differ across OSes, and headless Linux servers lack Tkinter (causing immediate crashes).",
        how_handled="Enabled Windows DPI awareness via SetProcessDpiAwareness(1), selected fonts dynamically based on sys.platform, and built an automatic CLI fallback if Tkinter is missing.",
        affected_os="Windows, Linux, macOS",
    ),
    ChallengeItem(
        id=9,
        title="Investigating multiple OSes from a single developer machine",
        what_happened="Developing cross-platform compatibility software on a single Windows laptop without VMs or cloud CI makes verifying Linux/macOS behavior difficult.",
        how_handled="Engineered an honest three-tier evidence model: MEASURED on host, SIMULATED for pure algorithms (PurePosixPath), and REFERENCE for documented OS specifications.",
        affected_os="All Platforms",
    ),
    ChallengeItem(
        id=10,
        title="Packaging and binary distribution limitations",
        what_happened="PyInstaller packages executables for the host OS only—a Windows PyInstaller .exe will not execute on Linux or macOS.",
        how_handled="Kept the codebase 100% standard library Python with zero external dependencies so that the raw source runs cleanly anywhere with just python main.py.",
        affected_os="All Platforms",
    ),
]
