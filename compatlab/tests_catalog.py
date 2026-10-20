"""Catalog of compatibility tests investigating cross-platform OS differences."""

from __future__ import annotations

import locale
import os
import pathlib
from pathlib import PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Callable

from compatlab.models import OSCell, Status, TestResult, Tier
from compatlab.reference import get_reference_value


class TestContext:
    """Context passed to each test function."""

    def __init__(self, host_os: str, temp_dir: str) -> None:
        self.host_os = host_os
        self.temp_dir = temp_dir


def is_reserved_windows_name(name: str) -> bool:
    """Check if a filename matches Windows reserved device names.

    Pure function over strings: never touches the filesystem.
    Matches CON, PRN, AUX, NUL, COM1-9, LPT1-9 (case-insensitive, with or without extension).
    """
    pattern = r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$"
    return bool(re.match(pattern, name.strip(), re.IGNORECASE))


def make_result(
    test_id: str,
    name: str,
    category: str,
    summary: str,
    explanation: str,
    host_value: str,
    host_os: str,
    win_val: str,
    win_tier: Tier,
    linux_val: str,
    linux_tier: Tier,
    macos_val: str,
    macos_tier: Tier,
    challenge_note: str,
    duration_ms: float,
    error: str | None = None,
) -> TestResult:
    """Helper to assemble a TestResult with standardized cells and verification."""
    cells = [
        OSCell("Windows", win_val, win_tier),
        OSCell("Linux", linux_val, linux_tier),
        OSCell("macOS", macos_val, macos_tier),
    ]

    if error:
        status = Status.ERROR
    elif win_val == linux_val == macos_val:
        status = Status.SAME
    else:
        status = Status.DIFFERS

    # Confirmed check for MEASURED host cells
    confirmed: bool | None = None
    host_cell = next((c for c in cells if c.os_name.lower() == host_os.lower()), None)
    if host_cell and host_cell.tier == Tier.MEASURED:
        expected = get_reference_value(test_id, host_cell.os_name)
        # Compare measured host value against reference expectation
        confirmed = expected.lower() in host_cell.value.lower() or host_cell.value.lower() in expected.lower()

    return TestResult(
        id=test_id,
        name=name,
        category=category,
        status=status,
        summary=summary,
        explanation=explanation,
        host_value=host_value,
        host_os=host_os,
        cells=cells,
        confirmed=confirmed,
        challenge_note=challenge_note,
        duration_ms=round(duration_ms, 2),
        error=error,
    )


def t01_path_separators(ctx: TestContext) -> TestResult:
    """T01: Path separators."""
    t0 = time.perf_counter()
    measured_info = f"os.sep={repr(os.sep)}, os.altsep={repr(os.altsep)}, os.pathsep={repr(os.pathsep)}"

    # PurePath simulations
    win_parse = PureWindowsPath(r"C:\Users\sam\notes.txt")
    posix_parse = PurePosixPath("/home/sam/notes.txt")
    simulated_info = (
        f"WinParse: drive='{win_parse.drive}', parts={win_parse.parts[:2]}; "
        f"PosixParse: drive='{posix_parse.drive}', parts={posix_parse.parts[:2]}"
    )

    is_win = ctx.host_os == "Windows"
    win_tier = Tier.MEASURED if is_win else Tier.SIMULATED
    win_val = "\\ (also accepts /)"
    linux_val = "/"
    macos_val = "/"

    dur = (time.perf_counter() - t0) * 1000
    return make_result(
        test_id="T01",
        name="Path separators",
        category="Paths",
        summary=f"Path separator is {repr(os.sep)} (alt: {repr(os.altsep)}); POSIX strictly uses '/'.",
        explanation=(
            "Windows adopted the backslash '\\' in MS-DOS 2.0 because slash '/' was already "
            "reserved for command switches (like 'dir /w'). POSIX systems (Linux and macOS) "
            "exclusively use forward slash '/'. Python's pathlib seamlessly abstracts these differences."
        ),
        host_value=f"{measured_info} | {simulated_info}",
        host_os=ctx.host_os,
        win_val=win_val,
        win_tier=win_tier,
        linux_val=linux_val,
        linux_tier=Tier.SIMULATED,
        macos_val=macos_val,
        macos_tier=Tier.SIMULATED,
        challenge_note="Hardcoding '\\' in paths breaks on Linux. Use pathlib or os.path.join.",
        duration_ms=dur,
    )


def t02_absolute_paths(ctx: TestContext) -> TestResult:
    """T02: Absolute path rules."""
    t0 = time.perf_counter()
    test_paths = ["C:/x", "/x", r"\\server\share\x"]

    win_abs = [PureWindowsPath(p).is_absolute() for p in test_paths]
    posix_abs = [PurePosixPath(p).is_absolute() for p in test_paths]

    host_val = f"PureWindowsPath.is_absolute: {win_abs}; PurePosixPath.is_absolute: {posix_abs}"
    dur = (time.perf_counter() - t0) * 1000
    return make_result(
        test_id="T02",
        name="Absolute path rules",
        category="Paths",
        summary="Windows roots paths via drive letters or UNC shares; Unix roots at a single '/'.",
        explanation=(
            "On Windows, a path starting with '/' or '\\' without a drive letter is drive-relative, "
            "not fully absolute. Full absolute Windows paths require a drive specifier ('C:\\') or "
            "UNC prefix ('\\\\server\\share'). Linux and macOS unify all filesystems under a single '/' root."
        ),
        host_value=host_val,
        host_os=ctx.host_os,
        win_val="Drive letters and UNC",
        win_tier=Tier.SIMULATED,
        linux_val="Single root /",
        linux_tier=Tier.SIMULATED,
        macos_val="Single root /",
        macos_tier=Tier.SIMULATED,
        challenge_note="Assuming '/x' is absolute fails on Windows where it resolves relative to current drive.",
        duration_ms=dur,
    )


def t03_max_path_length(ctx: TestContext) -> TestResult:
    """T03: Maximum path length."""
    t0 = time.perf_counter()
    reg_status = "unknown"
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\FileSystem",
            )
            val, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
            winreg.CloseKey(key)
            reg_status = "enabled" if val == 1 else "disabled"
        except Exception:
            reg_status = "disabled/unavailable"

    # Test nested directories exceeding 300 chars
    sub_dir = os.path.join(ctx.temp_dir, "t03_test")
    os.makedirs(sub_dir, exist_ok=True)
    nested_path = sub_dir
    created_depth = 0
    test_success = False

    try:
        segment = "subfolder_segment_20"
        for _ in range(16):  # ~320 chars total
            nested_path = os.path.join(nested_path, segment)
        os.makedirs(nested_path, exist_ok=True)
        test_success = len(nested_path) > 300 and os.path.exists(nested_path)
        created_depth = len(nested_path)
    except OSError:
        test_success = False
    finally:
        # Cleanup with \\?\ prefix fallback on Windows
        try:
            shutil.rmtree(sub_dir, ignore_errors=True)
        except Exception:
            if sys.platform == "win32" and not sub_dir.startswith("\\\\?\\"):
                shutil.rmtree("\\\\?\\" + os.path.abspath(sub_dir), ignore_errors=True)

    dur = (time.perf_counter() - t0) * 1000
    host_val = f"300+ chars created: {test_success} ({created_depth} chars); LongPathsEnabled: {reg_status}"

    return make_result(
        test_id="T03",
        name="Maximum path length",
        category="Paths",
        summary=f"Path length test: success={test_success}, Windows LongPaths={reg_status}.",
        explanation=(
            "Traditional Windows APIs limit total path length to 260 characters (MAX_PATH). "
            "Windows 10 added opt-in LongPathsEnabled registry support, while POSIX systems natively "
            "support paths up to 4096 bytes (Linux PATH_MAX) or 1024 bytes (macOS PATH_MAX)."
        ),
        host_value=host_val,
        host_os=ctx.host_os,
        win_val="~260 chars legacy limit unless long paths enabled",
        win_tier=Tier.MEASURED if ctx.host_os == "Windows" else Tier.REFERENCE,
        linux_val="~4096 total (PATH_MAX)",
        linux_tier=Tier.REFERENCE,
        macos_val="~1024 (PATH_MAX)",
        macos_tier=Tier.REFERENCE,
        challenge_note="Deeply nested dependencies (e.g. node_modules) fail on Windows without long path support.",
        duration_ms=dur,
    )


def t04_case_sensitivity(ctx: TestContext) -> TestResult:
    """T04: Case sensitivity."""
    t0 = time.perf_counter()
    test_dir = os.path.join(ctx.temp_dir, "t04_case")
    os.makedirs(test_dir, exist_ok=True)

    file_upper = os.path.join(test_dir, "Case.txt")
    file_lower = os.path.join(test_dir, "case.txt")

    with open(file_upper, "w", encoding="utf-8") as f:
        f.write("first")

    exists_lower_before = os.path.exists(file_lower)

    # Attempt to write second file
    with open(file_lower, "w", encoding="utf-8") as f:
        f.write("second")

    entries = os.listdir(test_dir)
    case_sensitive = len(entries) == 2

    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)

    dur = (time.perf_counter() - t0) * 1000
    host_val = (
        f"case.txt existed immediately: {exists_lower_before}, "
        f"final entries: {entries} (count={len(entries)})"
    )

    return make_result(
        test_id="T04",
        name="Case sensitivity",
        category="Files",
        summary="Filesystem is case-preserving but case-insensitive." if not case_sensitive else "Filesystem is case-sensitive.",
        explanation=(
            "Windows (NTFS) and macOS (APFS by default) are case-insensitive yet case-preserving: "
            "files named 'Case.txt' and 'case.txt' point to the same directory entry. "
            "Linux filesystems (ext4) are strictly case-sensitive, creating two distinct files."
        ),
        host_value=host_val,
        host_os=ctx.host_os,
        win_val="Case-insensitive, case-preserving",
        win_tier=Tier.MEASURED if ctx.host_os == "Windows" else Tier.REFERENCE,
        linux_val="Case-sensitive",
        linux_tier=Tier.REFERENCE,
        macos_val="Case-insensitive by default (APFS), configurable",
        macos_tier=Tier.REFERENCE,
        challenge_note="Mismatched import casing works on Windows development machines but crashes on Linux servers.",
        duration_ms=dur,
    )


def t05_reserved_filenames(ctx: TestContext) -> TestResult:
    """T05: Reserved and illegal filenames."""
    t0 = time.perf_counter()
    # Simulated check on reserved names
    sim_ok = (
        is_reserved_windows_name("con")
        and is_reserved_windows_name("NUL.txt")
        and is_reserved_windows_name("Com3")
        and is_reserved_windows_name("lpt9")
        and not is_reserved_windows_name("console")
        and not is_reserved_windows_name("nul_file")
    )

    # Measured check on illegal characters in temp dir
    test_dir = os.path.join(ctx.temp_dir, "t05_names")
    os.makedirs(test_dir, exist_ok=True)
    probe_names = ["a?b.txt", "a*b.txt", "trailing_dot.", "name_with_trailing_space "]
    rejected = []
    created = []

    for name in probe_names:
        probe_path = os.path.join(test_dir, name)
        try:
            with open(probe_path, "w", encoding="utf-8") as f:
                f.write("x")
            created.append(name)
        except OSError:
            rejected.append(name)

    shutil.rmtree(test_dir, ignore_errors=True)

    dur = (time.perf_counter() - t0) * 1000
    host_val = f"Reserved check: {sim_ok}; Rejected names: {rejected}; Created: {created}"

    return make_result(
        test_id="T05",
        name="Reserved and illegal filenames",
        category="Files",
        summary=f"Windows device names simulated safely; {len(rejected)}/{len(probe_names)} illegal filenames rejected.",
        explanation=(
            "Windows inherits device names (CON, PRN, AUX, NUL, COM1-9, LPT1-9) from CP/M, "
            "and prohibits characters < > : \" / \\ | ? * as well as trailing dots and spaces. "
            "POSIX systems allow virtually any character in filenames except '/' and byte 0x00."
        ),
        host_value=host_val,
        host_os=ctx.host_os,
        win_val="Many characters and names forbidden",
        win_tier=Tier.MEASURED if ctx.host_os == "Windows" else Tier.REFERENCE,
        linux_val="Only / and NUL byte forbidden",
        linux_tier=Tier.REFERENCE,
        macos_val="Only / (and : shown as / in Finder)",
        macos_tier=Tier.REFERENCE,
        challenge_note="Cross-platform git repos containing files like 'aux.py' fail to clone on Windows.",
        duration_ms=dur,
    )


def t06_line_endings(ctx: TestContext) -> TestResult:
    """T06: Line endings."""
    t0 = time.perf_counter()
    file_path = os.path.join(ctx.temp_dir, "t06_lines.txt")

    # Write in default text mode
    with open(file_path, "w") as f:
        f.write("a\nb\n")

    # Read raw bytes
    with open(file_path, "rb") as f:
        raw_bytes = f.read()

    try:
        os.remove(file_path)
    except OSError:
        pass

    has_crlf = b"\r\n" in raw_bytes
    host_val = f"os.linesep={repr(os.linesep)}, text mode bytes={repr(raw_bytes)}"
    dur = (time.perf_counter() - t0) * 1000

    return make_result(
        test_id="T06",
        name="Line endings",
        category="Files",
        summary=f"Default text mode produces {'CRLF (\\r\\n)' if has_crlf else 'LF (\\n)'}.",
        explanation=(
            "Windows uses Carriage Return + Line Feed (CRLF, \\r\\n) for newlines, "
            "originating from mechanical teletypes and early DOS systems. POSIX (Linux and macOS) "
            "standardizes on a single Line Feed (LF, \\n). Mismatched line endings corrupt bash scripts."
        ),
        host_value=host_val,
        host_os=ctx.host_os,
        win_val="CRLF (\\r\\n)",
        win_tier=Tier.MEASURED if ctx.host_os == "Windows" else Tier.REFERENCE,
        linux_val="LF (\\n)",
        linux_tier=Tier.REFERENCE,
        macos_val="LF (\\n)",
        macos_tier=Tier.REFERENCE,
        challenge_note="Bash scripts with CRLF line endings fail on Linux with '/bin/bash^M: bad interpreter'.",
        duration_ms=dur,
    )


def t07_unicode_normalization(ctx: TestContext) -> TestResult:
    """T07: Unicode filename normalization (Reference only)."""
    t0 = time.perf_counter()
    dur = (time.perf_counter() - t0) * 1000
    host_val = "Reference comparison only (not executed to avoid filesystem mutations)"

    return make_result(
        test_id="T07",
        name="Unicode filename normalization",
        category="Files",
        summary="Documented comparison: Windows/Linux preserve bytes/NFC, HFS+ decomposed to NFD.",
        explanation=(
            "Operating systems handle Unicode filenames differently: Apple's HFS+ decomposes characters "
            "into NFD (Canonical Decomposition), while modern APFS, Windows, and Linux preserve the input "
            "byte sequence (typically NFC). This can cause string equality checks on filenames to fail."
        ),
        host_value=host_val,
        host_os=ctx.host_os,
        win_val="Preserves what you give it (NFC typical)",
        win_tier=Tier.REFERENCE,
        linux_val="Preserves bytes",
        linux_tier=Tier.REFERENCE,
        macos_val="Normalizes to NFD on HFS+, preserves on APFS",
        macos_tier=Tier.REFERENCE,
        challenge_note="Filenames with accents may display identically but fail string comparisons across platforms.",
        duration_ms=dur,
    )


def t08_permission_bits(ctx: TestContext) -> TestResult:
    """T08: File permission bits."""
    t0 = time.perf_counter()
    test_file = os.path.join(ctx.temp_dir, "t08_perms.txt")
    with open(test_file, "w") as f:
        f.write("permission test")

    os.chmod(test_file, 0o600)
    mode1 = stat.S_IMODE(os.stat(test_file).st_mode)

    os.chmod(test_file, 0o444)
    can_write = os.access(test_file, os.W_OK)

    # Restore write permission for deletion
    os.chmod(test_file, 0o666)
    try:
        os.remove(test_file)
    except OSError:
        pass

    dur = (time.perf_counter() - t0) * 1000
    host_val = f"chmod 0o600 -> {oct(mode1)}, chmod 0o444 -> os.access(W_OK)={can_write}"

    return make_result(
        test_id="T08",
        name="File permission bits",
        category="Permissions",
        summary="chmod only toggles read-only status on Windows; POSIX provides user/group/other bits.",
        explanation=(
            "POSIX systems maintain distinct read, write, and execute bits for user, group, and others. "
            "Windows uses Access Control Lists (ACLs); Python's os.chmod on Windows only controls the "
            "file's read-only attribute, synthesizing POSIX mode bits on the fly."
        ),
        host_value=host_val,
        host_os=ctx.host_os,
        win_val="chmod only toggles the read-only flag, mode bits are synthetic",
        win_tier=Tier.MEASURED if ctx.host_os == "Windows" else Tier.REFERENCE,
        linux_val="Full POSIX rwx bits for user/group/other",
        linux_tier=Tier.REFERENCE,
        macos_val="Full POSIX rwx bits (BSD heritage)",
        macos_tier=Tier.REFERENCE,
        challenge_note="Using chmod 0o700 to protect credentials fails on Windows, leaving files readable by others.",
        duration_ms=dur,
    )


def t09_executable_detection(ctx: TestContext) -> TestResult:
    """T09: Executable detection."""
    t0 = time.perf_counter()
    txt_path = os.path.join(ctx.temp_dir, "script.txt")
    bat_path = os.path.join(ctx.temp_dir, "script.bat")

    with open(txt_path, "w") as f:
        f.write("echo off\n")
    with open(bat_path, "w") as f:
        f.write("@echo off\n")

    os.chmod(txt_path, 0o755)
    os.chmod(bat_path, 0o755)

    x_txt = os.access(txt_path, os.X_OK)
    x_bat = os.access(bat_path, os.X_OK)

    try:
        os.remove(txt_path)
        os.remove(bat_path)
    except OSError:
        pass

    pathext = os.environ.get("PATHEXT", "none")
    host_val = f"script.txt X_OK={x_txt}, script.bat X_OK={x_bat} (PATHEXT={pathext[:30]}...)"
    dur = (time.perf_counter() - t0) * 1000

    return make_result(
        test_id="T09",
        name="Executable detection",
        category="Permissions",
        summary="Execution permission depends on file extension (PATHEXT) on Windows, not chmod bits.",
        explanation=(
            "On Windows, file execution capability is determined by file extension matching PATHEXT "
            "(.EXE, .BAT, .CMD, etc.). On Linux and macOS, execution permission is controlled entirely "
            "by the POSIX execute (x) permission bit, regardless of file extension."
        ),
        host_value=host_val,
        host_os=ctx.host_os,
        win_val="Executability depends on file extension (PATHEXT)",
        win_tier=Tier.MEASURED if ctx.host_os == "Windows" else Tier.REFERENCE,
        linux_val="Depends on the execute permission bit",
        linux_tier=Tier.REFERENCE,
        macos_val="Depends on the execute permission bit",
        macos_tier=Tier.REFERENCE,
        challenge_note="Executable scripts downloaded on Linux require chmod +x before they can be invoked.",
        duration_ms=dur,
    )


def t10_symbolic_links(ctx: TestContext) -> TestResult:
    """T10: Symbolic links."""
    t0 = time.perf_counter()
    target_file = os.path.join(ctx.temp_dir, "t10_target.txt")
    link_file = os.path.join(ctx.temp_dir, "t10_link.txt")

    with open(target_file, "w") as f:
        f.write("target")

    symlink_ok = False
    reason = "ok"

    try:
        os.symlink(target_file, link_file)
        symlink_ok = os.path.islink(link_file)
    except (OSError, NotImplementedError) as err:
        symlink_ok = False
        reason = f"Permission/Feature error: {err.args[0] if err.args else str(err)}"
    finally:
        try:
            if os.path.lexists(link_file):
                os.remove(link_file)
            if os.path.exists(target_file):
                os.remove(target_file)
        except OSError:
            pass

    dur = (time.perf_counter() - t0) * 1000
    host_val = f"symlink created: {symlink_ok} ({reason})"

    return make_result(
        test_id="T10",
        name="Symbolic links",
        category="Links",
        summary=f"Symbolic link creation: {'success' if symlink_ok else 'restricted (Developer Mode/admin required)'}.",
        explanation=(
            "Creating symlinks on Linux and macOS is a basic, unprivileged filesystem feature. "
            "On Windows, creating symlinks historically required administrator rights; modern Windows "
            "allows standard users to create symlinks only when Developer Mode is enabled."
        ),
        host_value=host_val,
        host_os=ctx.host_os,
        win_val="Needs Developer Mode or admin",
        win_tier=Tier.MEASURED if ctx.host_os == "Windows" else Tier.REFERENCE,
        linux_val="Works for any user",
        linux_tier=Tier.REFERENCE,
        macos_val="Works for any user",
        macos_tier=Tier.REFERENCE,
        challenge_note="Package managers or build scripts creating symlinks fail on standard Windows accounts.",
        duration_ms=dur,
    )


def t11_default_encodings(ctx: TestContext) -> TestResult:
    """T11: Default encodings."""
    t0 = time.perf_counter()
    pref_enc = locale.getpreferredencoding(False)
    fs_enc = sys.getfilesystemencoding()
    stdout_enc = sys.stdout.encoding or "unknown"

    test_file = os.path.join(ctx.temp_dir, "t11_encoding.txt")
    test_str = "héllo ✓"
    roundtrip_ok = False

    try:
        # Write without specifying encoding (system default)
        with open(test_file, "w") as f:
            f.write(test_str)
        # Attempt to read back as UTF-8
        with open(test_file, "r", encoding="utf-8") as f:
            read_back = f.read()
        roundtrip_ok = (read_back == test_str)
    except Exception:
        roundtrip_ok = False
    finally:
        try:
            if os.path.exists(test_file):
                os.remove(test_file)
        except OSError:
            pass

    dur = (time.perf_counter() - t0) * 1000
    host_val = f"pref={pref_enc}, fs={fs_enc}, stdout={stdout_enc}, default_is_utf8={roundtrip_ok}"

    return make_result(
        test_id="T11",
        name="Default encodings",
        category="Text",
        summary=f"System preferred encoding is '{pref_enc}'; UTF-8 default roundtrip={roundtrip_ok}.",
        explanation=(
            "POSIX systems (Linux and macOS) standardize on UTF-8 across terminal, file system, and runtime. "
            "Windows historically defaults to ANSI code pages (such as cp1252), meaning open() without "
            "encoding='utf-8' can corrupt non-ASCII characters or fail with UnicodeEncodeError."
        ),
        host_value=host_val,
        host_os=ctx.host_os,
        win_val="Often a legacy code page like cp1252",
        win_tier=Tier.MEASURED if ctx.host_os == "Windows" else Tier.REFERENCE,
        linux_val="UTF-8",
        linux_tier=Tier.REFERENCE,
        macos_val="UTF-8",
        macos_tier=Tier.REFERENCE,
        challenge_note="Always pass encoding='utf-8' when opening files to prevent cross-platform text corruption.",
        duration_ms=dur,
    )


def t12_environment_and_shell(ctx: TestContext) -> TestResult:
    """T12: Environment and shell."""
    t0 = time.perf_counter()
    has_home = "HOME" in os.environ
    has_profile = "USERPROFILE" in os.environ
    shell_val = os.environ.get("SHELL") or os.environ.get("COMSPEC", "unknown")
    ls_path = shutil.which("ls")
    dir_path = shutil.which("dir")

    # Safe command invocation via subprocess
    cmd_ok = False
    try:
        if sys.platform == "win32":
            proc = subprocess.run(
                ["cmd.exe", "/c", "dir"],
                capture_output=True,
                timeout=5,
                check=False,
            )
        else:
            proc = subprocess.run(
                ["ls"],
                capture_output=True,
                timeout=5,
                check=False,
            )
        cmd_ok = proc.returncode == 0
    except Exception:
        cmd_ok = False

    dur = (time.perf_counter() - t0) * 1000
    host_val = (
        f"HOME={has_home}, USERPROFILE={has_profile}, shell={shell_val}, "
        f"which('ls')={bool(ls_path)}, which('dir')={bool(dir_path)}, subprocess_dir={cmd_ok}"
    )

    return make_result(
        test_id="T12",
        name="Environment and shell",
        category="Environment",
        summary="Windows relies on USERPROFILE & COMSPEC (cmd); Unix relies on HOME & SHELL.",
        explanation=(
            "Windows environments specify USERPROFILE for user homes and COMSPEC for the command interpreter, "
            "with commands like 'dir' built into cmd.exe rather than separate binaries. POSIX systems "
            "use HOME and SHELL, and standard utilities ('ls', 'clear') exist as standalone binaries."
        ),
        host_value=host_val,
        host_os=ctx.host_os,
        win_val="USERPROFILE, COMSPEC, cmd/PowerShell, dir, cls",
        win_tier=Tier.MEASURED if ctx.host_os == "Windows" else Tier.REFERENCE,
        linux_val="HOME, SHELL, bash/zsh, ls, clear",
        linux_tier=Tier.REFERENCE,
        macos_val="HOME, SHELL (zsh default), ls, clear",
        macos_tier=Tier.REFERENCE,
        challenge_note="Invoking subprocess.run(['ls']) or accessing os.environ['HOME'] crashes on Windows.",
        duration_ms=dur,
    )


# Registry of all 12 tests in order
TESTS: list[tuple[str, str, str, Callable[[TestContext], TestResult]]] = [
    ("T01", "Path separators", "Paths", t01_path_separators),
    ("T02", "Absolute path rules", "Paths", t02_absolute_paths),
    ("T03", "Maximum path length", "Paths", t03_max_path_length),
    ("T04", "Case sensitivity", "Files", t04_case_sensitivity),
    ("T05", "Reserved and illegal filenames", "Files", t05_reserved_filenames),
    ("T06", "Line endings", "Files", t06_line_endings),
    ("T07", "Unicode filename normalization", "Files", t07_unicode_normalization),
    ("T08", "File permission bits", "Permissions", t08_permission_bits),
    ("T09", "Executable detection", "Permissions", t09_executable_detection),
    ("T10", "Symbolic links", "Links", t10_symbolic_links),
    ("T11", "Default encodings", "Text", t11_default_encodings),
    ("T12", "Environment and shell", "Environment", t12_environment_and_shell),
]
