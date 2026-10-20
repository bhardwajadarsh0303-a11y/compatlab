"""Main entry point for CompatLab: Launches Tkinter GUI by default with automatic CLI fallback."""

from __future__ import annotations

import os
import sys

from compatlab.cli import parse_cli_args, run_cli


def main() -> int:
    """Determine runtime mode and execute GUI or CLI."""
    cli_flags = {"--cli", "--version", "--list", "--only", "--json", "--html", "-h", "--help"}
    has_cli_flags = any(arg in cli_flags for arg in sys.argv[1:])
    force_cli = os.environ.get("COMPATLAB_FORCE_CLI") == "1"

    if has_cli_flags or force_cli:
        args = parse_cli_args(sys.argv[1:])
        return run_cli(args)

    # Attempt to launch GUI
    try:
        import tkinter
        from compatlab.gui import launch_gui

        return launch_gui()
    except (ImportError, tkinter.TclError) as exc:
        print(f"GUI unavailable ({exc}). Falling back to CLI mode.", file=sys.stderr)
        args = parse_cli_args(["--cli"] + sys.argv[1:])
        return run_cli(args)
    except Exception as exc:
        print(f"GUI failed to start ({exc}). Falling back to CLI mode.", file=sys.stderr)
        args = parse_cli_args(["--cli"] + sys.argv[1:])
        return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
