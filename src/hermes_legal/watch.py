from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from .analysis.engine import analyze_contract
from .ingest import read_document, SUPPORTED_EXTENSIONS
from .providers import get_provider
from .reports import render_markdown_report


def _post_webhook(url: str, message: str) -> None:
    """
    Post an alert to a Slack or Discord incoming webhook (or any endpoint
    that accepts a JSON body). Sends both "text" (Slack) and "content"
    (Discord) keys so the same call works for either without the caller
    needing to specify which kind of webhook it is.
    """
    payload = json.dumps({"text": message, "content": message}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.URLError:
        pass  # best-effort; a failed notification should never crash watch mode


def run_watch_mode(
    folder: str,
    provider_name: str = "auto",
    perspective: str = "neutral",
    console=None,
    poll_seconds: float = 2.0,
    webhook_url: Optional[str] = None,
    alert_on: Optional[list] = None,
):
    """Poll a folder for new contract files and analyze each one as it appears.

    Uses simple polling (mtime + filename set) instead of a filesystem
    events library so there is no extra dependency required for this
    feature to work. If webhook_url is set, posts an alert to Slack or
    Discord whenever a newly analyzed contract's risk level is in
    alert_on (default: CRITICAL and HIGH).
    """
    if console is None:
        from rich.console import Console
        console = Console()

    alert_on = alert_on or ["CRITICAL", "HIGH"]
    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)
    provider = get_provider(provider_name)

    console.print(f"[cyan]Watching {folder_path} for new contracts (provider: {provider.name}). Ctrl+C to stop.[/]")
    if webhook_url:
        console.print(f"[dim]Webhook alerts enabled for: {', '.join(alert_on)}[/]")

    reports_dir = folder_path / "hermes_reports"
    reports_dir.mkdir(exist_ok=True)
    seen = {p.name for p in folder_path.iterdir() if p.is_file()}
    processed = []

    try:
        while True:
            current = {p for p in folder_path.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS}
            for p in sorted(current, key=lambda x: x.name):
                if p.name in seen:
                    continue
                seen.add(p.name)
                console.print(f"\n[bold]New file detected:[/] {p.name}")
                try:
                    text = read_document(p)
                    outcome = analyze_contract(text, provider=provider, perspective=perspective)
                    result = outcome["result"]
                    console.print(
                        f"  -> {result.overall_risk} risk, verdict {result.verdict} "
                        f"({len(outcome['red_flags'])} red flag(s))"
                    )
                    report_path = reports_dir / f"{p.stem}_report.md"
                    report_path.write_text(
                        render_markdown_report(result, outcome["hash"], outcome["trend"]), encoding="utf-8"
                    )
                    console.print(f"  Report: {report_path}")
                    processed.append(p.name)

                    if webhook_url and result.overall_risk in alert_on:
                        message = (
                            f"Hermes Legal Advisor: *{p.name}* scored {result.overall_risk} risk "
                            f"(verdict: {result.verdict}, {len(outcome['red_flags'])} red flag(s)). "
                            f"Contract type: {result.contract_type}."
                        )
                        _post_webhook(webhook_url, message)
                        console.print("  [dim]Webhook alert sent.[/]")
                except Exception as exc:
                    console.print(f"  [red]Failed to analyze {p.name}: {exc}[/]")
            time.sleep(poll_seconds)
    except KeyboardInterrupt:
        console.print(f"\n[dim]Watch mode stopped. Analyzed {len(processed)} contract(s) total.[/]")
