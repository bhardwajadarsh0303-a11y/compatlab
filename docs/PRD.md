# PRD: CompatLab, a Cross-Platform OS Compatibility Lab

## 1. Context
Course project (PBL) problem statement: "Cross-Platform Compatibility: Investigate how different operating systems handle compatibility. Develop a project that includes writing a simple application that runs on multiple OS platforms, highlighting the challenges faced."

Developer environment: a single Windows 10/11 machine. No Linux, macOS, WSL, VM, or cloud CI is available or wanted.
Developer: one student, vibe coding with an AI assistant. Code must be simple, readable, and easy to debug.
Deadline: tomorrow. Simplicity and reliability beat feature count.

## 2. Product Summary
CompatLab is a small Python desktop app (Tkinter GUI with a CLI fallback) that investigates how Windows, Linux and macOS differ in the way they handle files, paths, permissions, encodings, shells and more.
It is portable: the same source code runs unchanged on Windows, Linux and macOS. On any OS it runs a battery of small compatibility tests and explains the differences.

Because only Windows is available to the developer, CompatLab uses an honest three-tier evidence model so that it can still compare all three operating systems:
- **MEASURED** (green): The test actually ran on the machine the app is running on.
- **SIMULATED** (blue): The test ran real code that implements another OS's rules (e.g. `pathlib.PurePosixPath` and `pathlib.PureWindowsPath`).
- **REFERENCE** (grey): Documented behavior of an OS that could not be executed here. Stored in a built-in knowledge base with a short source note.

Hard rule: the app must never present REFERENCE or SIMULATED data as MEASURED. Every cell in the comparison matrix carries its tier badge.

## 3. Goals and Non-Goals
### Goals
1. One codebase that runs on Windows, Linux and macOS without modification.
2. At least 12 compatibility tests across 6 categories, each with an explanation.
3. A clean, modern-looking Tkinter GUI plus a CLI fallback.
4. Export reports to JSON and a self-contained HTML file.
5. A comparison matrix of Windows vs Linux vs macOS with evidence tier badges.
6. A built-in "Challenges Faced" section (required by the problem statement).
7. Pushable to GitHub with a good README. Zero third-party dependencies.

### Non-Goals
- No GitHub Actions, no CI, no cloud services, no network calls.
- No installing or emulating other operating systems.
- No databases, no web server, no external GUI toolkits.
- No admin or root privileges required. Never modify anything outside its own temporary folder.

## 4. Tech Stack and Constraints
- Python 3.10 or newer. Standard library only.
- Type hints and short docstrings everywhere. Functions under about 40 lines.
- Temporary files inside `tempfile.TemporaryDirectory()`, cleaned up even on failure (`try/finally`).
- Every test wrapped so one failing test never crashes the app.
- Subprocess calls: fixed safe commands only, `timeout=5`, `capture_output=True`.
- Never create or open Windows reserved device names (`CON`, `NUL`, `AUX`, `PRN`, `COM1-9`, `LPT1-9`).
