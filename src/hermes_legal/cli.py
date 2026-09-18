from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from . import __version__
from .analysis.engine import analyze_contract, compare_contracts
from .analysis.risk import RISK_COLORS, RISK_ICONS, VERDICT_COLORS, VERDICT_ICONS
from .ingest import read_document, SUPPORTED_EXTENSIONS
from .memory.store import MemoryStore
from .providers import AUTO_DETECT_ORDER, PROVIDER_REGISTRY, ProviderError, get_provider
from .reports import render_markdown_report, render_redline_markdown, write_batch_csv, write_redline_docx

console = Console(width=min(110, __import__("shutil").get_terminal_size().columns))

DISCLAIMER = (
    "Hermes Legal Advisor provides contract analysis, not legal advice. "
    "Always consult a qualified attorney before signing any contract."
)


def _print_result(result, contract_hash: str, trend: Optional[str]):
    t = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
    t.add_column("Field", style="dim", width=20)
    t.add_column("Value")
    t.add_row("Contract Type", result.contract_type)
    t.add_row("Parties", result.parties)
    t.add_row("Language", result.language)
    t.add_row("Provider", result.provider)
    t.add_row(
        "Overall Risk",
        f"[{RISK_COLORS.get(result.overall_risk, 'white')}]"
        f"{RISK_ICONS.get(result.overall_risk, '')} {result.overall_risk}[/]",
    )
    t.add_row(
        "Verdict",
        f"[{VERDICT_COLORS.get(result.verdict, 'white')}]"
        f"{VERDICT_ICONS.get(result.verdict, '')} {result.verdict}[/]",
    )
    if trend:
        t.add_row("Trend", trend)
    t.add_row("Hash", contract_hash)
    console.print(t)

    if result.clauses:
        ct = Table(title="Clause Scoring", box=box.SIMPLE, show_header=True, header_style="bold")
        ct.add_column("Clause")
        ct.add_column("Score")
        ct.add_column("Red Flag")
        ct.add_column("Finding", overflow="fold")
        for c in result.clauses:
            ct.add_row(
                str(c.get("name", "")),
                f"{c.get('score', '')}/10",
                "\U0001F6A8" if c.get("is_red_flag") else "",
                str(c.get("finding", "")),
            )
        console.print(ct)

    if result.missing_clauses:
        console.print("\n[bold yellow]Missing Clauses:[/]")
        for m in result.missing_clauses:
            console.print(f"  \u26A0\uFE0F  {m}")

    if result.recommendations:
        console.print("\n[bold green]Recommended Actions:[/]")
        for i, rec in enumerate(result.recommendations, 1):
            console.print(f"  {i}. {rec}")


def cmd_providers(args):
    console.print(Panel(f"Hermes Legal Advisor v{__version__} - available providers", border_style="cyan"))
    t = Table(box=box.SIMPLE, header_style="bold")
    t.add_column("Provider")
    t.add_column("Status")
    t.add_column("Notes")
    notes = {
        "groq": "Free tier. Set GROQ_API_KEY. https://console.groq.com/keys",
        "gemini": "Free tier. Set GEMINI_API_KEY. https://aistudio.google.com/apikey",
        "openrouter": "Free models available (':free' suffix). Set OPENROUTER_API_KEY.",
        "ollama": "Fully local and free. Requires `ollama serve` running.",
        "offline": "Zero-dependency rule-based scanner. Always available, no key needed.",
    }
    for name in AUTO_DETECT_ORDER:
        available = PROVIDER_REGISTRY[name]().is_available()
        status = "[green]available[/]" if available else "[dim]not configured[/]"
        t.add_row(name, status, notes.get(name, ""))
    console.print(t)


def cmd_analyze(args):
    if not Path(args.contract).exists():
        console.print(f"[red]File not found: {args.contract}[/]")
        sys.exit(1)

    try:
        text = read_document(args.contract)
    except Exception as exc:
        console.print(f"[red]Could not read {args.contract}: {exc}[/]")
        sys.exit(1)

    try:
        provider = get_provider(args.provider)
    except ProviderError as exc:
        console.print(f"[red]{exc}[/]")
        sys.exit(1)

    console.print(f"[dim]Using provider: {provider.name}[/]")
    with console.status("[cyan]Analyzing contract...[/]"):
        try:
            outcome = analyze_contract(
                text, provider=provider, perspective=args.perspective, save=not args.no_save
            )
        except ProviderError as exc:
            console.print(f"[red]{exc}[/]")
            sys.exit(1)

    result = outcome["result"]
    _print_result(result, outcome["hash"], outcome["trend"])

    if args.output:
        report = render_markdown_report(result, outcome["hash"], outcome["trend"])
        Path(args.output).write_text(report, encoding="utf-8")
        console.print(f"\n[dim]Report saved to {args.output}[/]")

    if args.redline:
        redline_md = render_redline_markdown(result)
        Path(args.redline).write_text(redline_md, encoding="utf-8")
        console.print(f"[dim]Redline (Markdown) saved to {args.redline}[/]")

    if args.redline_docx:
        saved = write_redline_docx(result, args.redline_docx)
        if saved:
            console.print(f"[dim]Redline (DOCX) saved to {saved}[/]")
        else:
            console.print("[yellow]python-docx not installed; skipped DOCX redline. "
                          "Install with: pip install python-docx[/]")

    console.print(f"\n[dim]{DISCLAIMER}[/]")

    if args.fail_on_risk and result.overall_risk in [r.strip().upper() for r in args.fail_on_risk.split(",")]:
        sys.exit(2)


def cmd_batch(args):
    folder = Path(args.folder)
    if not folder.is_dir():
        console.print(f"[red]Not a folder: {folder}[/]")
        sys.exit(1)

    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    if not files:
        console.print(f"[yellow]No supported contract files found in {folder}[/]")
        return

    provider = get_provider(args.provider)
    console.print(f"[dim]Using provider: {provider.name} | {len(files)} file(s)[/]")

    memory = MemoryStore()
    rows = []
    reports_dir = Path(args.reports_dir) if args.reports_dir else folder / "hermes_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        console.print(f"\n[bold]-> {f.name}[/]")
        try:
            text = read_document(f)
            outcome = analyze_contract(text, provider=provider, perspective=args.perspective, memory=memory)
        except Exception as exc:
            console.print(f"  [red]Failed: {exc}[/]")
            rows.append({"file": f.name, "contract_type": "ERROR", "overall_risk": "", "verdict": str(exc)})
            continue

        result = outcome["result"]
        _print_result(result, outcome["hash"], outcome["trend"])
        report_path = reports_dir / f"{f.stem}_report.md"
        report_path.write_text(render_markdown_report(result, outcome["hash"], outcome["trend"]), encoding="utf-8")

        rows.append(
            {
                "file": f.name,
                "contract_type": result.contract_type,
                "parties": result.parties,
                "language": result.language,
                "overall_risk": result.overall_risk,
                "verdict": result.verdict,
                "red_flag_count": len(outcome["red_flags"]),
                "clause_count": len(result.clauses),
                "provider": result.provider,
                "hash": outcome["hash"],
            }
        )

    csv_path = write_batch_csv(rows, reports_dir / "batch_summary.csv")
    console.print(f"\n[bold green]Batch complete.[/] Summary: {csv_path}")
    console.print(f"Per-file reports: {reports_dir}")


def cmd_compare(args):
    text_a = read_document(args.v1)
    text_b = read_document(args.v2)
    provider = get_provider(args.provider)

    with console.status("[cyan]Comparing versions...[/]"):
        diff = compare_contracts(text_a, text_b, provider=provider)

    t = Table(title="Version Comparison", box=box.SIMPLE, header_style="bold")
    t.add_column("Clause")
    t.add_column("v1 score")
    t.add_column("v2 score")
    t.add_column("Status")
    status_style = {"IMPROVED": "green", "WORSE": "red", "UNCHANGED": "dim", "ADDED": "cyan", "REMOVED": "yellow"}
    for row in diff["rows"]:
        style = status_style.get(row["status"], "white")
        t.add_row(
            row["clause"],
            str(row["score_v1"]) if row["score_v1"] is not None else "-",
            str(row["score_v2"]) if row["score_v2"] is not None else "-",
            f"[{style}]{row['status']}[/]",
        )
    console.print(t)
    if diff["risk_changed"]:
        console.print(
            f"\n[bold]Overall risk changed: {diff['v1'].overall_risk} -> {diff['v2'].overall_risk}[/]"
        )
    console.print(f"\n[dim]{DISCLAIMER}[/]")


def cmd_watch(args):
    from .watch import run_watch_mode

    run_watch_mode(args.folder, provider_name=args.provider, perspective=args.perspective, console=console)


def cmd_chat(args):
    from .chat import run_chat_mode

    run_chat_mode(provider_name=args.provider, console=console)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermes-legal",
        description="Hermes Legal Advisor - free, multi-provider AI contract analysis.",
    )
    parser.add_argument("--version", action="version", version=f"hermes-legal {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    common_provider = dict(
        default="auto",
        help="LLM backend to use: groq, gemini, openrouter, ollama, offline, or auto (default: auto-detect).",
    )

    p_analyze = sub.add_parser("analyze", help="Analyze a single contract file.")
    p_analyze.add_argument("contract", help="Path to a .txt, .md, .pdf, or .docx contract file.")
    p_analyze.add_argument("--provider", **common_provider)
    p_analyze.add_argument(
        "--perspective", default="neutral",
        help="Whose side you're reviewing for: client, vendor, contractor, employer, employee, tenant, landlord, neutral.",
    )
    p_analyze.add_argument("--output", help="Save the full Markdown report to this path.")
    p_analyze.add_argument("--redline", help="Save a Markdown redline (only flagged clauses) to this path.")
    p_analyze.add_argument("--redline-docx", help="Save a DOCX redline memo to this path (requires python-docx).")
    p_analyze.add_argument("--no-save", action="store_true", help="Do not write this analysis to memory.")
    p_analyze.add_argument(
        "--fail-on-risk", default=None,
        help="Comma-separated risk levels that should cause a non-zero exit code (useful in CI), e.g. CRITICAL,HIGH",
    )
    p_analyze.set_defaults(func=cmd_analyze)

    p_batch = sub.add_parser("batch", help="Analyze every contract in a folder.")
    p_batch.add_argument("folder", help="Folder containing contract files.")
    p_batch.add_argument("--provider", **common_provider)
    p_batch.add_argument("--perspective", default="neutral")
    p_batch.add_argument("--reports-dir", default=None, help="Where to write per-file reports and the CSV summary.")
    p_batch.set_defaults(func=cmd_batch)

    p_compare = sub.add_parser("compare", help="Compare two versions of a contract.")
    p_compare.add_argument("v1", help="Path to the first (older) version.")
    p_compare.add_argument("v2", help="Path to the second (newer) version.")
    p_compare.add_argument("--provider", **common_provider)
    p_compare.set_defaults(func=cmd_compare)

    p_watch = sub.add_parser("watch", help="Watch a folder and auto-analyze new contracts dropped into it.")
    p_watch.add_argument("folder", help="Folder to watch.")
    p_watch.add_argument("--provider", **common_provider)
    p_watch.add_argument("--perspective", default="neutral")
    p_watch.set_defaults(func=cmd_watch)

    p_chat = sub.add_parser("chat", help="Interactive chat about your analyzed contracts.")
    p_chat.add_argument("--provider", **common_provider)
    p_chat.set_defaults(func=cmd_chat)

    p_providers = sub.add_parser("providers", help="List available providers and their configuration status.")
    p_providers.set_defaults(func=cmd_providers)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
