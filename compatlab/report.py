"""Report serialization and generation for CompatLab (JSON, HTML, plain text)."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path

from compatlab.challenges import CHALLENGES
from compatlab.models import HostInfo, OSCell, Report, Status, TestResult, Tier, to_dict


def to_json(report: Report, path: str | Path) -> None:
    """Export report to a pretty-printed UTF-8 JSON file."""
    data = {
        "schema_version": 1,
        **to_dict(report),
    }
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def from_json(path: str | Path) -> Report:
    """Load a previously exported Report from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    host_data = data["host"]
    host = HostInfo(
        os_name=host_data["os_name"],
        os_release=host_data["os_release"],
        os_version=host_data["os_version"],
        machine=host_data["machine"],
        python_version=host_data["python_version"],
        python_implementation=host_data["python_implementation"],
        filesystem_encoding=host_data["filesystem_encoding"],
        preferred_encoding=host_data["preferred_encoding"],
        stdout_encoding=host_data["stdout_encoding"],
        cpu_count=host_data.get("cpu_count"),
        timestamp_iso=host_data["timestamp_iso"],
    )

    results: list[TestResult] = []
    for r in data["results"]:
        cells = [
            OSCell(
                os_name=c["os_name"],
                value=c["value"],
                tier=Tier(c["tier"]),
            )
            for c in r["cells"]
        ]
        results.append(
            TestResult(
                id=r["id"],
                name=r["name"],
                category=r["category"],
                status=Status(r["status"]),
                summary=r["summary"],
                explanation=r["explanation"],
                host_value=r["host_value"],
                host_os=r["host_os"],
                cells=cells,
                confirmed=r.get("confirmed"),
                challenge_note=r.get("challenge_note", ""),
                duration_ms=r.get("duration_ms", 0.0),
                error=r.get("error"),
            )
        )

    return Report(
        app_version=data.get("app_version", "1.0.0"),
        host=host,
        results=results,
        summary=data["summary"],
    )


def to_text_summary(report: Report) -> str:
    """Format report as plain text for console copy and CLI output."""
    lines = [
        "===========================================================",
        f"CompatLab v{report.app_version} - Cross-Platform Compatibility Report",
        "===========================================================",
        f"Host: {report.host.os_name} {report.host.os_release} ({report.host.machine})",
        f"Python: {report.host.python_version} ({report.host.python_implementation})",
        f"Encodings: Preferred={report.host.preferred_encoding}, FS={report.host.filesystem_encoding}",
        f"Timestamp: {report.host.timestamp_iso}",
        "-----------------------------------------------------------",
        f"Total Tests: {report.summary['total']} | Differs: {report.summary['differs']} | "
        f"Same: {report.summary['same']} | Confirmed: {report.summary['confirmed']} | Errors: {report.summary['errors']}",
        "-----------------------------------------------------------",
    ]
    for r in report.results:
        conf_tag = f" [Confirmed: {r.confirmed}]" if r.confirmed is not None else ""
        lines.append(f"[{r.id}] {r.name} ({r.category}): {r.status.value}{conf_tag}")
        lines.append(f"  Summary: {r.summary}")
        lines.append(f"  This Machine: {r.host_value}")
        for c in r.cells:
            lines.append(f"    - {c.os_name} [{c.tier.value}]: {c.value}")
        lines.append("")
    return "\n".join(lines)


def to_html(report: Report, path: str | Path) -> None:
    """Generate a self-contained HTML report with inline CSS and print styling."""
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    tier_badge_classes = {
        Tier.MEASURED: "badge-measured",
        Tier.SIMULATED: "badge-simulated",
        Tier.REFERENCE: "badge-reference",
    }

    rows_html = []
    for r in report.results:
        cells_by_os = {c.os_name: c for c in r.cells}
        win_c = cells_by_os.get("Windows")
        lin_c = cells_by_os.get("Linux")
        mac_c = cells_by_os.get("macOS")

        def cell_markup(c: OSCell | None) -> str:
            if not c:
                return "<td>N/A</td>"
            cls_name = tier_badge_classes.get(c.tier, "badge-reference")
            return (
                f"<td>"
                f"  <span class='badge {cls_name}'>{html.escape(c.tier.value)}</span> "
                f"  <span>{html.escape(c.value)}</span>"
                f"</td>"
            )

        status_class = "status-differs" if r.status == Status.DIFFERS else "status-same"
        if r.status == Status.ERROR:
            status_class = "status-error"

        row = f"""
        <tr>
          <td><strong>{html.escape(r.id)}</strong></td>
          <td>
            <strong>{html.escape(r.name)}</strong><br>
            <span class="subtext">{html.escape(r.category)}</span>
            <details class="details-box">
              <summary>Explanation & Pitfall</summary>
              <p><strong>Why OSes differ:</strong> {html.escape(r.explanation)}</p>
              <p><strong>Observed on this host:</strong> <code>{html.escape(r.host_value)}</code></p>
              <p><strong>Developer Pitfall:</strong> {html.escape(r.challenge_note)}</p>
            </details>
          </td>
          <td><span class="badge {status_class}">{html.escape(r.status.value)}</span></td>
          {cell_markup(win_c)}
          {cell_markup(lin_c)}
          {cell_markup(mac_c)}
        </tr>
        """
        rows_html.append(row)

    challenges_cards_html = []
    for c in CHALLENGES:
        card = f"""
        <div class="card challenge-card">
          <h3>{c.id}. {html.escape(c.title)}</h3>
          <p><span class="badge badge-reference">{html.escape(c.affected_os)}</span></p>
          <p><strong>What happens:</strong> {html.escape(c.what_happened)}</p>
          <p><strong>How it was solved:</strong> {html.escape(c.how_handled)}</p>
        </div>
        """
        challenges_cards_html.append(card)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>CompatLab Report - {html.escape(report.host.os_name)}</title>
  <style>
    :root {{
      --bg: #F5F7FA;
      --surface: #FFFFFF;
      --text: #0F172A;
      --muted: #64748B;
      --primary: #2563EB;
      --success: #16A34A;
      --warning: #D97706;
      --error: #DC2626;
      --border: #E2E8F0;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      margin: 0;
      padding: 24px;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    header {{
      background: var(--surface);
      border-radius: 8px;
      padding: 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      margin-bottom: 24px;
    }}
    h1 {{ margin: 0 0 8px 0; font-size: 26px; color: var(--primary); }}
    .tagline {{ color: var(--muted); font-size: 14px; margin: 0; }}
    .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .card {{
      background: var(--surface);
      border-radius: 8px;
      padding: 16px 20px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      border: 1px solid var(--border);
    }}
    .metric-value {{ font-size: 28px; font-weight: bold; color: var(--text); }}
    .metric-label {{ font-size: 13px; color: var(--muted); text-transform: uppercase; font-weight: 600; }}
    .legend-bar {{
      background: var(--surface);
      border-radius: 8px;
      padding: 12px 20px;
      margin-bottom: 24px;
      border: 1px solid var(--border);
      font-size: 14px;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .badge-measured {{ background: #DCFCE7; color: #15803D; }}
    .badge-simulated {{ background: #DBEAFE; color: #1D4ED8; }}
    .badge-reference {{ background: #F1F5F9; color: #475569; }}
    .status-differs {{ background: #FEF3C7; color: #B45309; }}
    .status-same {{ background: #DCFCE7; color: #15803D; }}
    .status-error {{ background: #FEE2E2; color: #B91C1C; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--surface);
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      border: 1px solid var(--border);
      margin-bottom: 32px;
    }}
    th, td {{
      padding: 12px 14px;
      text-align: left;
      border-bottom: 1px solid var(--border);
      font-size: 13px;
      vertical-align: top;
    }}
    th {{
      background: #F8FAFC;
      color: var(--muted);
      font-weight: 600;
      font-size: 12px;
      text-transform: uppercase;
    }}
    tr:last-child td {{ border-bottom: none; }}
    .subtext {{ font-size: 12px; color: var(--muted); }}
    details.details-box {{
      margin-top: 8px;
      font-size: 12px;
      background: #F8FAFC;
      padding: 8px 10px;
      border-radius: 6px;
      border: 1px solid var(--border);
    }}
    details summary {{ cursor: pointer; color: var(--primary); font-weight: 600; }}
    .challenge-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }}
    .challenge-card h3 {{ margin: 0 0 6px 0; font-size: 15px; }}
    .challenge-card p {{ margin: 4px 0; font-size: 13px; }}
    @media print {{
      body {{ background: white; padding: 0; }}
      .card, table, header {{ box-shadow: none; border: 1px solid #ccc; }}
      details {{ display: block !important; }}
      details summary {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>CompatLab v{html.escape(report.app_version)}</h1>
      <p class="tagline">Same code. Different operating systems. Cross-Platform OS Compatibility Report.</p>
      <div style="margin-top: 12px; font-size: 13px; color: var(--muted);">
        <strong>Host:</strong> {html.escape(report.host.os_name)} {html.escape(report.host.os_release)} ({html.escape(report.host.machine)}) |
        <strong>Python:</strong> {html.escape(report.host.python_version)} |
        <strong>Time:</strong> {html.escape(report.host.timestamp_iso)}
      </div>
    </header>

    <div class="card-grid">
      <div class="card">
        <div class="metric-label">Total Tests</div>
        <div class="metric-value">{report.summary['total']}</div>
      </div>
      <div class="card">
        <div class="metric-label">OSes Differ</div>
        <div class="metric-value" style="color: var(--warning);">{report.summary['differs']}</div>
      </div>
      <div class="card">
        <div class="metric-label">Confirmed on Host</div>
        <div class="metric-value" style="color: var(--success);">{report.summary['confirmed']}</div>
      </div>
      <div class="card">
        <div class="metric-label">Errors</div>
        <div class="metric-value" style="color: var(--error);">{report.summary['errors']}</div>
      </div>
    </div>

    <div class="legend-bar">
      <strong>Three-Tier Evidence Model:</strong>
      <span class="badge badge-measured">MEASURED</span> Executed on this machine &bull;
      <span class="badge badge-simulated">SIMULATED</span> Pure-path algorithmic simulation &bull;
      <span class="badge badge-reference">REFERENCE</span> Documented OS specification.
      <em>(Only MEASURED values were observed on this machine.)</em>
    </div>

    <h2>Compatibility Results Table</h2>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Test & Description</th>
          <th>Status</th>
          <th>Windows</th>
          <th>Linux</th>
          <th>macOS</th>
        </tr>
      </thead>
      <tbody>
        {"".join(rows_html)}
      </tbody>
    </table>

    <h2>Challenges Faced in Cross-Platform Compatibility</h2>
    <div class="challenge-grid">
      {"".join(challenges_cards_html)}
    </div>
  </div>
</body>
</html>
"""
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(html_content)
