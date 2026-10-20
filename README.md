# CompatLab: Cross-Platform OS Compatibility Lab

A lightweight, zero-dependency Python desktop application and CLI tool that investigates how Windows, Linux, and macOS handle files, paths, permissions, encodings, and shell environments.

## Problem Statement

> "Cross-Platform Compatibility: Investigate how different operating systems handle compatibility. Develop a project that includes writing a simple application that runs on multiple OS platforms, highlighting the challenges faced."

## What It Does

CompatLab runs a battery of 12 compatibility tests across 6 key OS categories (Paths, Files, Permissions, Links, Text, and Environment). For every test, CompatLab explains why operating systems differ, detects common developer pitfalls, and displays a three-way comparison matrix of Windows vs Linux vs macOS.

CompatLab is built with an honest evidence model: when running on a Windows developer laptop, it genuinely measures Windows behavior, uses standard library pure-path classes to simulate POSIX behavior where mathematically exact, and clearly marks documented Linux/macOS behaviors as reference data.

## Screenshot Placeholders

```
+-----------------------------------------------------------------------------------------+
| CompatLab - Same code. Different operating systems.     [Running on: Windows 11 | 3.12] |
+-----------------------------------------------------------------------------------------+
| [Run Tests] [Compare] [Challenges] [About]                                              |
|                                                                                         |
| [ Run All Tests (Ctrl+R) ] [ Export JSON ] [ Export HTML ] [ Copy Summary ] Filter: All |
|                                                                                         |
| +------------------+ +------------------+ +------------------+ +------------------+     |
| | TOTAL TESTS:  12 | | OSES DIFFER:  12 | | CONFIRMED:    10 | | ERRORS:        0 |     |
| +------------------+ +------------------+ +------------------+ +------------------+     |
|                                                                                         |
| ID   Test                      Category     Status   Host Value                 Dur     |
| T01  Path separators           Paths        DIFFERS  os.sep='\\' altsep='/'     0.5 ms  |
| T02  Absolute path rules       Paths        DIFFERS  PureWindows vs PurePosix   0.8 ms  |
| T03  Maximum path length       Paths        DIFFERS  300+ chars: True, Reg=ok   2.1 ms  |
| T04  Case sensitivity          Files        DIFFERS  Case-insensitive           1.2 ms  |
| ...                                                                                     |
+-----------------------------------------------------------------------------------------+
```

## Quick Start

CompatLab requires Python 3.10 or newer and uses only the Python standard library. No packages need to be installed.

Run the Tkinter GUI:
```bash
python main.py
```
Or double-click `run.bat` on Windows.

Run in CLI mode:
```bash
python main.py --cli
```

Filter specific tests:
```bash
python main.py --cli --only T01,T04
```

Export reports to JSON and HTML:
```bash
python main.py --cli --json reports/report.json --html reports/report.html
```

List all available tests:
```bash
python main.py --list
```

## Requirements

- Python 3.10 or newer
- Zero third-party dependencies (Standard Library only: `tkinter`, `ttk`, `pathlib`, `os`, `sys`, `platform`, `json`, `subprocess`, `tempfile`, `shutil`, `stat`, `locale`, `argparse`, `dataclasses`, `datetime`, `html`, `threading`, `queue`, `webbrowser`, `unittest`).

## Three-Tier Evidence Model and Honesty Statement

CompatLab adheres to a strict honesty policy so that no claim is overstated:

- **MEASURED** (Green badge): The test actually executed on the machine hosting the app (e.g. Windows).
- **SIMULATED** (Blue badge): The test executed real code implementing another OS's rules (for example, `pathlib.PurePosixPath` parsing on Windows).
- **REFERENCE** (Grey badge): Documented behavior of an operating system that could not be executed locally. Stored in a built-in knowledge base with source citations.

Honesty Statement: The application never presents REFERENCE or SIMULATED data as MEASURED. Every cell in the comparison matrix carries its tier badge.

## List of Compatibility Tests

| ID | Category | Test Name | Windows | Linux | macOS |
|:---|:---|:---|:---|:---|:---|
| T01 | Paths | Path separators | \ (also accepts /) | / | / |
| T02 | Paths | Absolute path rules | Drive letters and UNC | Single root / | Single root / |
| T03 | Paths | Maximum path length | ~260 chars legacy limit | ~4096 total (PATH_MAX) | ~1024 (PATH_MAX) |
| T04 | Files | Case sensitivity | Case-insensitive, case-preserving | Case-sensitive | Case-insensitive by default |
| T05 | Files | Reserved & illegal filenames | Reserved device names forbidden | Only / and NUL byte forbidden | Only / (colon shown as /) |
| T06 | Files | Line endings | CRLF (\r\n) | LF (\n) | LF (\n) |
| T07 | Files | Unicode normalization | Preserves input (NFC typical) | Preserves bytes | NFD on HFS+, preserves on APFS |
| T08 | Permissions | File permission bits | Synthetic chmod (read-only toggle) | Full POSIX rwx bits | Full POSIX rwx bits |
| T09 | Permissions | Executable detection | File extension (PATHEXT) | Execute permission bit (x) | Execute permission bit (x) |
| T10 | Links | Symbolic links | Developer Mode or admin required | Works for any user | Works for any user |
| T11 | Text | Default encodings | Often legacy code page (cp1252) | UTF-8 | UTF-8 |
| T12 | Environment | Environment & shell | USERPROFILE, COMSPEC, dir, cls | HOME, SHELL, bash/zsh, ls | HOME, SHELL (zsh), ls |

## How to Export Reports

From the GUI:
1. Click "Run All Tests".
2. Click "Export JSON" or "Export HTML".
3. Choose the destination directory (defaults to `reports/`).

From the CLI:
```bash
python main.py --cli --json reports/my_report.json --html reports/my_report.html
```
The exported HTML report is a self-contained, single-file document with inline styling and print-friendly formatting.

## How to Run Unit Tests

To run the automated test engine suite:
```bash
python -m unittest discover tests
```

## Project Structure

```
compatlab/
|-- main.py              # Application entry point: GUI by default, CLI fallback
|-- compatlab/
|   |-- __init__.py      # Package metadata and version ("1.0.0")
|   |-- models.py        # Dataclasses (TestResult, OSCell, HostInfo, Report) and enums
|   |-- reference.py     # Built-in reference knowledge base
|   |-- tests_catalog.py # 12 test implementations and registry
|   |-- runner.py        # Suite runner, error isolation, host collection
|   |-- report.py        # JSON, HTML, and text summary generators
|   |-- challenges.py    # Pre-seeded cross-platform challenges data
|   |-- cli.py           # CLI parser and plain ASCII matrix renderer
|   `-- gui.py           # Modern Tkinter GUI with clamshell theme
|-- tests/
|   `-- test_engine.py   # Unittest suite verifying models, registry, and reports
|-- reports/             # Default destination for generated reports
|   `-- .gitkeep
|-- docs/
|   `-- PRD.md           # Product Requirements Document
|-- run.bat              # Windows double-click launcher
|-- README.md            # This documentation
|-- CHALLENGES.md        # Comprehensive challenges log
|-- requirements.txt     # Dependency list (standard library only)
|-- .gitignore           # Python and build exclusions
|-- .gitattributes       # Line ending normalization rules
`-- LICENSE              # MIT License
```

## Challenges Faced Summary

Developing cross-platform software surfaces numerous subtle system divergences:
1. Hardcoded path separators breaking when moving across Windows and Linux.
2. Case sensitivity causing bugs when filenames differ only in capitalization.
3. Line endings (CRLF vs LF) corrupting shell scripts on Linux.
4. Elevated privilege requirements for creating symbolic links on Windows.
5. Windows reserved device names (CON, PRN, AUX, NUL) causing crashes or checkout failures.
6. System encoding defaults corrupting Unicode text when encoding is omitted.
7. Discrepancies between Windows NTFS ACLs and POSIX permission bits.
8. GUI scaling and missing Tkinter libraries on headless Linux systems.
9. Investigating multiple operating systems from a single Windows developer laptop.
10. Binary packaging limitations with platform-specific PyInstaller bundles.

For full technical breakdowns and solutions, see [CHALLENGES.md](file:///c:/Users/Welcome/OneDrive/Desktop/internship/ol%20pbl/CHALLENGES.md).

## Optional PyInstaller Instructions

CompatLab requires no compilation. However, if you wish to bundle a standalone Windows executable:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```
The resulting executable will be placed in `dist/main.exe`. Note that a binary built on Windows will only run on Windows.

## Limitations

- REFERENCE tier data represents documented behavior per official operating system and filesystem specifications. It does not reflect modifications by non-standard kernel patches, custom filesystem drivers, or specialized enterprise group policies.
- Filesystem behavior can vary by filesystem type (e.g., FAT32 vs NTFS vs ReFS on Windows, ext4 vs Btrfs vs ZFS on Linux, APFS vs HFS+ on macOS).

## Credits

Developed for the Cross-Platform Compatibility Problem-Based Learning (PBL) Course Project. Released under the MIT License.
