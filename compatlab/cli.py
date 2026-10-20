"""Command-line interface and plain ASCII table renderer for CompatLab."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from compatlab import __version__
from compatlab.models import Report, Status, Tier
from compatlab.report import to_html, to_json
from compatlab.runner import run_all
from compatlab.tests_catalog import TESTS


def get_tier_marker(tier: Tier) -> str:
    """Return compact plain ASCII tier marker."""
    if tier == Tier.MEASURED:
        return "[M]"
    if tier == Tier.SIMULATED:
        return "[S]"
    return "[R]"


def format_cell_text(tier: Tier, val: str, max_len: int = 28) -> str:
    """Format single cell text with tier marker and length truncation."""
    marker = get_tier_marker(tier)
    text = f"{marker} {val}"
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text.ljust(max_len)


def render_ascii_table(report: Report) -> str:
    """Format report results as a clean, portable ASCII table."""
    col_w = {
        "id": 5,
        "name": 26,
        "status": 9,
        "win": 30,
        "lin": 28,
        "mac": 28,
    }

    border = (
        f"+-{'-' * col_w['id']}-"
        f"+-{'-' * col_w['name']}-"
        f"+-{'-' * col_w['status']}-"
        f"+-{'-' * col_w['win']}-"
        f"+-{'-' * col_w['lin']}-"
        f"+-{'-' * col_w['mac']}-+"
    )

    header = (
        f"| {'ID'.ljust(col_w['id'])} "
        f"| {'Test'.ljust(col_w['name'])} "
        f"| {'Status'.ljust(col_w['status'])} "
        f"| {'Windows'.ljust(col_w['win'])} "
        f"| {'Linux'.ljust(col_w['lin'])} "
        f"| {'macOS'.ljust(col_w['mac'])} |"
    )

    lines = [
        "",
        f"CompatLab v{report.app_version} - Cross-Platform OS Compatibility Matrix",
        f"Host: {report.host.os_name} {report.host.os_release} ({report.host.machine}) | Python: {report.host.python_version}",
        "Tiers: [M] MEASURED on this machine | [S] SIMULATED pure logic | [R] REFERENCE documented spec",
        border,
        header,
        border,
    ]

    for r in report.results:
        cells = {c.os_name: c for c in r.cells}
        win_c = cells.get("Windows")
        lin_c = cells.get("Linux")
        mac_c = cells.get("macOS")

        win_str = format_cell_text(win_c.tier, win_c.value, col_w["win"]) if win_c else "".ljust(col_w["win"])
        lin_str = format_cell_text(lin_c.tier, lin_c.value, col_w["lin"]) if lin_c else "".ljust(col_w["lin"])
        mac_str = format_cell_text(mac_c.tier, mac_c.value, col_w["mac"]) if mac_c else "".ljust(col_w["mac"])

        name_trunc = r.name[: col_w["name"]].ljust(col_w["name"])
        id_str = r.id.ljust(col_w["id"])
        status_str = r.status.value.ljust(col_w["status"])

        row = f"| {id_str} | {name_trunc} | {status_str} | {win_str} | {lin_str} | {mac_str} |"
        lines.append(row)

    lines.append(border)
    summary_line = (
        f"Summary: Total: {report.summary['total']} | "
        f"Differs: {report.summary['differs']} | "
        f"Same: {report.summary['same']} | "
        f"Confirmed on host: {report.summary['confirmed']} | "
        f"Errors: {report.summary['errors']}"
    )
    lines.append(summary_line)
    lines.append("")
    return "\n".join(lines)


def parse_cli_args(args: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="compatlab",
        description="CompatLab: Cross-Platform OS Compatibility Lab",
    )
    parser.add_argument("--cli", action="store_true", help="Run tests and output plain table to console")
    parser.add_argument("--version", action="store_true", help="Display version and exit")
    parser.add_argument("--list", action="store_true", help="List registered compatibility tests and exit")
    parser.add_argument("--only", type=str, default=None, help="Comma-separated test IDs to run (e.g. T01,T04)")
    parser.add_argument("--json", type=str, default=None, help="File path to save JSON report")
    parser.add_argument("--html", type=str, default=None, help="File path to save HTML report")
    return parser.parse_args(args)


def run_cli(args: argparse.Namespace) -> int:
    """Execute CLI actions and return process exit code."""
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    if args.version:
        print(f"CompatLab v{__version__}")
        return 0

    if args.list:
        print(f"\nCompatLab v{__version__} - Registered Tests:")
        print("--------------------------------------------------")
        for tid, name, cat, _ in TESTS:
            print(f"[{tid}] {name.ljust(30)} ({cat})")
        print("--------------------------------------------------\n")
        return 0

    only_ids = [s.strip() for s in args.only.split(",")] if args.only else None
    if only_ids:
        valid_ids = {t[0].lower() for t in TESTS}
        for item in only_ids:
            if item.lower() not in valid_ids:
                print(f"Error: Unknown test ID '{item}'. Run with --list to see available IDs.", file=sys.stderr)
                return 2

    report = run_all(only_ids=only_ids)
    print(render_ascii_table(report))

    if args.json:
        to_json(report, args.json)
        print(f"Report exported to JSON: {args.json}")

    if args.html:
        to_html(report, args.html)
        print(f"Report exported to HTML: {args.html}")

    return 1 if report.summary["errors"] > 0 else 0
