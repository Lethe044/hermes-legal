from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from .analysis.engine import analyze_contract
from .ingest import read_document, SUPPORTED_EXTENSIONS
from .providers import get_provider
from .reports import render_markdown_report


def run_watch_mode(
    folder: str,
    provider_name: str = "auto",
    perspective: str = "neutral",
    console=None,
    poll_seconds: float = 2.0,
):
    """Poll a folder for new contract files and analyze each one as it appears.

    Uses simple polling (mtime + filename set) instead of a filesystem
    events library so there is no extra dependency required for this
    feature to work.
    """
    if console is None:
        from rich.console import Console
        console = Console()

    folder_path = Path(folder)
    folder_path.mkdir(parents=True, exist_ok=True)
    provider = get_provider(provider_name)

    console.print(f"[cyan]Watching {folder_path} for new contracts (provider: {provider.name}). Ctrl+C to stop.[/]")

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
                except Exception as exc:
                    console.print(f"  [red]Failed to analyze {p.name}: {exc}[/]")
            time.sleep(poll_seconds)
    except KeyboardInterrupt:
        console.print(f"\n[dim]Watch mode stopped. Analyzed {len(processed)} contract(s) total.[/]")
