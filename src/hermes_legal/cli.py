from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from . import __version__
from .analysis.engine import analyze_contract, compare_contracts
from .analysis.risk import RISK_COLORS, RISK_ICONS, VERDICT_COLORS, VERDICT_ICONS
from .ingest import read_document, SUPPORTED_EXTENSIONS
from .memory.store import MemoryStore
from .playbook import DEFAULT_PLAYBOOK_PATH, Playbook, write_example_playbook
from .providers import AUTO_DETECT_ORDER, PROVIDER_REGISTRY, AnalysisResult, ProviderError, get_provider
from .reports import (
    render_markdown_report,
    render_redline_markdown,
    write_batch_csv,
    write_batch_dashboard,
    write_batch_xlsx,
    write_pdf_report,
    write_portfolio_dashboard,
    render_portfolio_dashboard,
    write_redline_docx,
    write_redline_docx_inline,
)

console = Console(width=min(110, __import__("shutil").get_terminal_size().columns))

DISCLAIMER = (
    "Hermes Legal Advisor provides contract analysis, not legal advice. "
    "Always consult a qualified attorney before signing any contract."
)


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


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

        if any(c.get("plain_explanation") for c in result.clauses):
            console.print("\n[bold cyan]In Plain English:[/]")
            for c in result.clauses:
                if c.get("plain_explanation"):
                    console.print(f"  [bold]{c.get('name')}:[/] {c.get('plain_explanation')}")

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

    for extra_path in args.include or []:
        p = Path(extra_path)
        if not p.exists():
            console.print(f"[red]--include file not found: {extra_path}[/]")
            sys.exit(1)
        try:
            extra_text = read_document(p)
        except Exception as exc:
            console.print(f"[red]Could not read {extra_path}: {exc}[/]")
            sys.exit(1)
        text += f"\n\n--- Exhibit: {p.name} ---\n\n{extra_text}"

    try:
        provider = get_provider(args.provider)
    except ProviderError as exc:
        console.print(f"[red]{exc}[/]")
        sys.exit(1)

    playbook = Playbook.load(args.playbook) if args.playbook or DEFAULT_PLAYBOOK_PATH.exists() else Playbook()
    quiet = args.format == "json"

    if not quiet:
        console.print(f"[dim]Using provider: {provider.name}[/]")
    status_ctx = console.status("[cyan]Analyzing contract...[/]") if not quiet else _NullContext()
    with status_ctx:
        try:
            outcome = analyze_contract(
                text, provider=provider, perspective=args.perspective, save=not args.no_save,
                playbook=playbook, explain=args.explain, allow_fallback=not args.no_fallback,
                use_cache=not args.no_cache, force=args.force, client=args.client,
            )
        except ProviderError as exc:
            if quiet:
                print(json.dumps({"error": str(exc)}))
            else:
                console.print(f"[red]{exc}[/]")
            sys.exit(1)

    result = outcome["result"]
    if outcome.get("from_cache") and not quiet:
        console.print("[dim]Identical contract already analyzed before - reusing cached result (no API call made). Use --force to re-analyze.[/]")
    if outcome.get("fallback_note") and not quiet:
        console.print(f"[yellow]{outcome['fallback_note']}[/]")
    if quiet:
        payload = result.to_dict()
        payload["hash"] = outcome["hash"]
        payload["trend"] = outcome["trend"]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_result(result, outcome["hash"], outcome["trend"])

    if args.output:
        report = render_markdown_report(result, outcome["hash"], outcome["trend"])
        Path(args.output).write_text(report, encoding="utf-8")
        if not quiet:
            console.print(f"\n[dim]Report saved to {args.output}[/]")

    if args.redline:
        redline_md = render_redline_markdown(result)
        Path(args.redline).write_text(redline_md, encoding="utf-8")
        if not quiet:
            console.print(f"[dim]Redline (Markdown) saved to {args.redline}[/]")

    if args.redline_docx:
        saved = write_redline_docx(result, args.redline_docx)
        if not quiet:
            if saved:
                console.print(f"[dim]Redline (DOCX) saved to {saved}[/]")
            else:
                console.print("[yellow]python-docx not installed; skipped DOCX redline. "
                              "Install with: pip install python-docx[/]")

    if args.redline_inline:
        if Path(args.contract).suffix.lower() != ".docx":
            if not quiet:
                console.print("[yellow]--redline-inline only works on .docx input files; skipped.[/]")
        else:
            saved = write_redline_docx_inline(args.contract, result, args.redline_inline)
            if not quiet:
                if saved:
                    console.print(f"[dim]Inline redline (edited copy of your .docx) saved to {saved}[/]")
                else:
                    console.print("[yellow]Could not produce inline redline (python-docx missing, or no clauses could be matched in the document text).[/]")

    if args.output_pdf:
        saved = write_pdf_report(result, outcome["hash"], outcome["trend"], args.output_pdf, firm_name=playbook.firm_name)
        if not quiet:
            if saved:
                console.print(f"[dim]PDF report saved to {saved}[/]")
            else:
                console.print("[yellow]reportlab not installed; skipped PDF export. "
                              "Install with: pip install reportlab[/]")

    if not quiet:
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
    console.print(f"[dim]Using provider: {provider.name} | {len(files)} file(s) | parallel={args.parallel}[/]")

    memory = MemoryStore()
    reports_dir = Path(args.reports_dir) if args.reports_dir else folder / "hermes_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    def _process(f: Path):
        try:
            text = read_document(f)
            outcome = analyze_contract(text, provider=provider, perspective=args.perspective, memory=memory, client=args.client)
            return f, outcome, None
        except Exception as exc:
            return f, None, exc

    results = []
    if args.parallel and args.parallel > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with console.status(f"[cyan]Analyzing {len(files)} contract(s) with {args.parallel} worker(s)...[/]"):
            with ThreadPoolExecutor(max_workers=args.parallel) as executor:
                futures = {executor.submit(_process, f): f for f in files}
                for future in as_completed(futures):
                    results.append(future.result())
        results.sort(key=lambda r: r[0].name)
    else:
        for f in files:
            results.append(_process(f))

    rows = []
    for f, outcome, exc in results:
        console.print(f"\n[bold]-> {f.name}[/]")
        if exc is not None:
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
    dashboard_path = write_batch_dashboard(rows, reports_dir / "dashboard.html")
    console.print(f"\n[bold green]Batch complete.[/] Summary: {csv_path}")
    console.print(f"Dashboard: {dashboard_path}")

    if args.output_xlsx:
        xlsx_path = write_batch_xlsx(rows, args.output_xlsx)
        if xlsx_path:
            console.print(f"Excel report: {xlsx_path}")
        else:
            console.print("[yellow]openpyxl not installed; skipped Excel export. Install with: pip install openpyxl[/]")

    console.print(f"Per-file reports: {reports_dir}")

    if not args.no_browser:
        import webbrowser
        try:
            webbrowser.open(dashboard_path.resolve().as_uri())
        except Exception:
            pass


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

    alert_on = [a.strip().upper() for a in args.alert_on.split(",")] if args.alert_on else None
    run_watch_mode(
        args.folder, provider_name=args.provider, perspective=args.perspective, console=console,
        webhook_url=args.webhook, alert_on=alert_on,
    )


def cmd_chat(args):
    from .chat import run_chat_mode

    run_chat_mode(provider_name=args.provider, console=console)


def cmd_playbook_init(args):
    path = write_example_playbook(args.path)
    console.print(f"[green]Example playbook written to {path}[/]")
    console.print("[dim]Edit it to set your firm name, override clause scores, or add custom rules.[/]")


def cmd_history(args):
    memory = MemoryStore()
    contracts = memory.contracts()
    if args.client:
        contracts = [c for c in contracts if c.get("client") == args.client]
    if args.query:
        contracts = [c for c in contracts if args.query.lower() in str(c).lower()]
    if not contracts:
        console.print("[yellow]No analyzed contracts found.[/]")
        return
    t = Table(box=box.SIMPLE, header_style="bold")
    for col in ("Date", "Type", "Parties", "Risk", "Verdict", "Provider", "Hash"):
        t.add_column(col)
    for c in contracts[-args.limit:][::-1]:
        t.add_row(
            str(c.get("timestamp", ""))[:10],
            str(c.get("contract_type", "")),
            str(c.get("parties", ""))[:40],
            f"[{RISK_COLORS.get(c.get('risk_level'), 'white')}]{c.get('risk_level', '')}[/]",
            str(c.get("verdict", "")),
            str(c.get("provider", "")),
            str(c.get("contract_hash", "")),
        )
    console.print(t)


def cmd_generate(args):
    from .generator import CONTRACT_TEMPLATES, generate_contract

    if args.list:
        t = Table(title="Available Templates", box=box.SIMPLE, header_style="bold")
        t.add_column("Key")
        t.add_column("Name")
        t.add_column("Fields")
        for key, tpl in CONTRACT_TEMPLATES.items():
            t.add_row(key, tpl["name"], ", ".join(tpl["fields"]))
        console.print(t)
        return

    if args.template not in CONTRACT_TEMPLATES:
        console.print(f"[red]Unknown template '{args.template}'. Run 'hermes-legal generate --list' to see options.[/]")
        sys.exit(1)

    answers: Dict[str, str] = {}
    for kv in args.field or []:
        if "=" not in kv:
            console.print(f"[red]--field must be key=value, got: {kv}[/]")
            sys.exit(1)
        k, v = kv.split("=", 1)
        answers[k.strip()] = v.strip()

    tpl = CONTRACT_TEMPLATES[args.template]
    missing = [f for f in tpl["fields"] if f not in answers]
    if missing and not args.interactive:
        console.print(f"[yellow]Missing fields, using placeholders: {', '.join(missing)}[/]")
    elif missing and args.interactive:
        for f in missing:
            answers[f] = console.input(f"[bold]{f}:[/] ").strip()

    text = generate_contract(args.template, answers)
    out_path = Path(args.output or f"{args.template}_generated.txt")
    out_path.write_text(text, encoding="utf-8")
    console.print(f"[green]Generated contract written to {out_path}[/]")
    console.print(f"\n[dim]{DISCLAIMER}[/]")


def cmd_serve(args):
    from .webapp import run_server

    api_key = args.api_key or os.environ.get("HERMES_LEGAL_API_KEY")
    run_server(host=args.host, port=args.port, provider_name=args.provider, open_browser=not args.no_browser, api_key=api_key)


def cmd_ask(args):
    from .ask import ask_contract

    if not Path(args.contract).exists():
        console.print(f"[red]File not found: {args.contract}[/]")
        sys.exit(1)
    try:
        text = read_document(args.contract)
    except Exception as exc:
        console.print(f"[red]Could not read {args.contract}: {exc}[/]")
        sys.exit(1)

    provider = get_provider(args.provider)
    with console.status(f"[cyan]Asking {provider.name}...[/]"):
        try:
            answer = ask_contract(text, args.question, provider)
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/]")
            sys.exit(1)

    console.print(Panel(answer, title=args.question, border_style="cyan"))
    console.print(f"\n[dim]{DISCLAIMER}[/]")


def cmd_deadlines(args):
    memory = MemoryStore()
    obligations = memory.all_obligations()
    dated = [o for o in obligations if o.get("days") is not None]
    dated.sort(key=lambda o: o["days"])

    if not dated:
        console.print("[yellow]No time-bound obligations extracted yet. Analyze some contracts first.[/]")
        return

    t = Table(title="Upcoming / Notable Obligations (soonest first)", box=box.SIMPLE, header_style="bold")
    for col in ("Kind", "Description", "~Days", "Contract Type", "Parties", "Analyzed"):
        t.add_column(col)
    for o in dated[: args.limit]:
        t.add_row(
            str(o.get("kind", "")),
            str(o.get("description", "")),
            str(o.get("days", "")),
            str(o.get("contract_type", "")),
            str(o.get("parties", ""))[:30],
            str(o.get("analyzed_at", ""))[:10],
        )
    console.print(t)
    console.print(
        "\n[dim]Days are approximate durations extracted from contract text "
        "(term length, notice period, renewal window) - not calendar deadlines "
        "unless an explicit date was also found in the contract.[/]"
    )


def cmd_export(args):
    import csv as csv_module
    import io
    import zipfile

    memory = MemoryStore()
    contracts = memory.contracts()
    if args.client:
        contracts = [c for c in contracts if c.get("client") == args.client]
    contracts = [c for c in contracts if c.get("full_result")]
    if not contracts:
        console.print("[yellow]No matching contracts with full results found to export.[/]")
        return

    out_path = Path(args.output or f"{(args.client or 'all').replace(' ', '_')}_bundle.zip")
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, c in enumerate(contracts, 1):
            result = AnalysisResult(**c["full_result"])
            report_md = render_markdown_report(result, c.get("contract_hash", ""), None)
            safe_name = f"{i:02d}_{result.contract_type.replace(' ', '_')}_{c.get('contract_hash', '')}.md"
            zf.writestr(safe_name, report_md)

        csv_rows = [
            {
                "file": c.get("contract_hash", ""),
                "contract_type": c.get("contract_type", ""),
                "parties": c.get("parties", ""),
                "overall_risk": c.get("risk_level", ""),
                "verdict": c.get("verdict", ""),
                "red_flag_count": len(c.get("flagged_clauses", []) or []),
                "clause_count": c.get("findings_count", ""),
                "provider": c.get("provider", ""),
                "hash": c.get("contract_hash", ""),
            }
            for c in contracts
        ]
        buf = io.StringIO()
        writer = csv_module.DictWriter(buf, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
        zf.writestr("summary.csv", buf.getvalue())
        zf.writestr("dashboard.html", render_portfolio_dashboard(contracts))

    console.print(f"[green]Exported {len(contracts)} contract(s) to {out_path}[/]")


def cmd_clients(args):
    memory = MemoryStore()
    clients = memory.clients()
    if not clients:
        console.print("[yellow]No client/matter tags found yet. Use --client when analyzing to start tagging.[/]")
        return
    t = Table(title="Clients / Matters", box=box.SIMPLE, header_style="bold")
    t.add_column("Client")
    t.add_column("Contracts")
    for client in clients:
        count = len(memory.find_by_client(client))
        t.add_row(client, str(count))
    console.print(t)


def cmd_portfolio(args):
    memory = MemoryStore()
    contracts = memory.contracts()
    if args.client:
        contracts = [c for c in contracts if c.get("client") == args.client]
    if not contracts:
        console.print("[yellow]No contracts analyzed yet.[/]")
        return

    out_path = Path(args.output or "portfolio_dashboard.html")
    saved = write_portfolio_dashboard(contracts, out_path)
    console.print(f"[green]Portfolio dashboard written to {saved}[/] ({len(contracts)} contract(s) all-time)")

    if not args.no_browser:
        import webbrowser
        try:
            webbrowser.open(saved.resolve().as_uri())
        except Exception:
            pass


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
    p_analyze.add_argument("--output-pdf", help="Save a professional PDF report to this path (requires reportlab).")
    p_analyze.add_argument("--redline", help="Save a Markdown redline (only flagged clauses) to this path.")
    p_analyze.add_argument("--redline-docx", help="Save a DOCX redline memo to this path (requires python-docx).")
    p_analyze.add_argument("--redline-inline", help="Save an edited copy of the original .docx with suggestions inserted inline (requires .docx input and python-docx).")
    p_analyze.add_argument("--playbook", default=None, help="Path to a firm playbook YAML file (default: ~/.hermes-legal/playbook.yaml if present).")
    p_analyze.add_argument("--format", choices=["text", "json"], default="text", help="Output format for stdout (default: text).")
    p_analyze.add_argument("--explain", action="store_true", help="Add plain-English explanations of each clause category.")
    p_analyze.add_argument("--no-fallback", action="store_true", help="Do not automatically fall back to another provider if the chosen one fails.")
    p_analyze.add_argument("--no-cache", action="store_true", help="Do not reuse a cached result for identical contract text.")
    p_analyze.add_argument("--force", action="store_true", help="Re-analyze even if this exact contract was analyzed before (bypasses cache).")
    p_analyze.add_argument("--include", action="append", help="Additional file(s) (exhibits/addenda) to append and analyze as one contract package. Repeatable.")
    p_analyze.add_argument("--client", default=None, help="Tag this analysis with a client/matter name for portfolio and history filtering.")
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
    p_batch.add_argument("--client", default=None, help="Tag every analysis in this batch with a client/matter name.")
    p_batch.add_argument("--output-xlsx", default=None, help="Also save a formatted Excel (.xlsx) summary (requires openpyxl).")
    p_batch.add_argument("--parallel", type=int, default=1, help="Number of contracts to analyze concurrently (useful with hosted LLM providers). Default: 1 (sequential).")
    p_batch.add_argument("--no-browser", action="store_true", help="Do not auto-open the generated HTML dashboard.")
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
    p_watch.add_argument("--webhook", default=None, help="Slack or Discord incoming webhook URL for risk alerts.")
    p_watch.add_argument("--alert-on", default="CRITICAL,HIGH", help="Comma-separated risk levels that trigger a webhook alert.")
    p_watch.set_defaults(func=cmd_watch)

    p_chat = sub.add_parser("chat", help="Interactive chat about your analyzed contracts.")
    p_chat.add_argument("--provider", **common_provider)
    p_chat.set_defaults(func=cmd_chat)

    p_providers = sub.add_parser("providers", help="List available providers and their configuration status.")
    p_providers.set_defaults(func=cmd_providers)

    p_playbook = sub.add_parser("playbook", help="Manage firm/personal playbook customization.")
    playbook_sub = p_playbook.add_subparsers(dest="playbook_command", required=True)
    p_playbook_init = playbook_sub.add_parser("init", help="Write an example playbook.yaml to customize.")
    p_playbook_init.add_argument("--path", default=None, help="Where to write it (default: ~/.hermes-legal/playbook.yaml)")
    p_playbook_init.set_defaults(func=cmd_playbook_init)

    p_clients = sub.add_parser("clients", help="List client/matter tags and how many contracts each has.")
    p_clients.set_defaults(func=cmd_clients)

    p_export = sub.add_parser("export", help="Bundle every report for a client (or everyone) into one ZIP.")
    p_export.add_argument("--client", default=None, help="Only export contracts tagged with this client. Omit to export everything.")
    p_export.add_argument("--output", default=None, help="Output ZIP path (default: <client>_bundle.zip).")
    p_export.set_defaults(func=cmd_export)

    p_history = sub.add_parser("history", help="Show previously analyzed contracts.")
    p_history.add_argument("--query", default=None, help="Filter by any text (party name, contract type, etc).")
    p_history.add_argument("--client", default=None, help="Filter to only this client/matter tag.")
    p_history.add_argument("--limit", type=int, default=20, help="Max rows to show (default 20).")
    p_history.set_defaults(func=cmd_history)

    p_generate = sub.add_parser("generate", help="Generate a new contract from a template, for free, offline.")
    p_generate.add_argument("template", nargs="?", default=None, help="Template key, e.g. nda, freelance, employment, service.")
    p_generate.add_argument("--list", action="store_true", help="List available templates and their fields.")
    p_generate.add_argument("--field", action="append", help="Set a field value as key=value. Repeatable.")
    p_generate.add_argument("--interactive", action="store_true", help="Prompt for any missing fields.")
    p_generate.add_argument("--output", default=None, help="Output file path.")
    p_generate.set_defaults(func=cmd_generate)

    p_serve = sub.add_parser("serve", help="Launch a local web dashboard for drag-and-drop contract analysis.")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8765)
    p_serve.add_argument("--provider", **common_provider)
    p_serve.add_argument("--no-browser", action="store_true", help="Do not auto-open a browser tab.")
    p_serve.add_argument("--api-key", default=None, help="Require this key (header X-API-Key or ?key= in the URL) to use the dashboard. Also read from HERMES_LEGAL_API_KEY. Strongly recommended if binding to a non-localhost host.")
    p_serve.set_defaults(func=cmd_serve)

    p_ask = sub.add_parser("ask", help="Ask a specific contract a direct question.")
    p_ask.add_argument("contract", help="Path to a .txt, .md, .pdf, or .docx contract file.")
    p_ask.add_argument("question", help="Your question, e.g. 'what is the termination notice period?'")
    p_ask.add_argument("--provider", **common_provider)
    p_ask.set_defaults(func=cmd_ask)

    p_deadlines = sub.add_parser("deadlines", help="List time-bound obligations extracted from analyzed contracts.")
    p_deadlines.add_argument("--limit", type=int, default=20)
    p_deadlines.set_defaults(func=cmd_deadlines)

    p_portfolio = sub.add_parser("portfolio", help="Generate an aggregate HTML dashboard across every contract ever analyzed.")
    p_portfolio.add_argument("--output", default=None, help="Output HTML path (default: portfolio_dashboard.html).")
    p_portfolio.add_argument("--client", default=None, help="Restrict the dashboard to only this client/matter tag.")
    p_portfolio.add_argument("--no-browser", action="store_true")
    p_portfolio.set_defaults(func=cmd_portfolio)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
