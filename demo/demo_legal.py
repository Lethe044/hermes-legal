#!/usr/bin/env python3
"""
Hermes Legal Advisor - Full Featured Demo
==========================================
Autonomous contract analysis agent that reads contracts,
scores every clause for risk, suggests negotiation language,
gives a final SIGN/NEGOTIATE/REJECT verdict, supports
Turkish and English, and remembers every contract it has
ever analyzed.

Requirements:  pip install openai rich
Setup:         set OPENROUTER_API_KEY=sk-or-...

Usage:
    python demo/demo_legal.py --contract sample_contracts/freelance_contract.txt
    python demo/demo_legal.py --contract sample_contracts/nda_contract.txt
    python demo/demo_legal.py --contract sample_contracts/employment_contract.txt
    python demo/demo_legal.py --contract sample_contracts/turkish_contract.txt
    python demo/demo_legal.py --chat
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.rule import Rule
    from rich.table import Table
    from rich.text import Text
    from rich import box
except ImportError:
    print("pip install rich")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("pip install openai")
    sys.exit(1)

import shutil
import concurrent.futures
console = Console(width=min(110, shutil.get_terminal_size().columns))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

LEGAL_DIR    = Path.home() / ".hermes" / "legal"
MEMORY_FILE  = LEGAL_DIR / "contracts_memory.jsonl"
REPORTS_DIR  = LEGAL_DIR / "reports"

for d in [LEGAL_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Risk styling
# ---------------------------------------------------------------------------

RISK_COLORS = {
    "CRITICAL": "bold red",
    "HIGH":     "bold yellow",
    "MEDIUM":   "yellow",
    "LOW":      "green",
}
RISK_ICONS = {
    "CRITICAL": "🔴",
    "HIGH":     "🟠",
    "MEDIUM":   "🟡",
    "LOW":      "🟢",
}
VERDICT_STYLES = {
    "SIGN":      ("bold green",  "✅"),
    "NEGOTIATE": ("bold yellow", "⚠️ "),
    "REJECT":    ("bold red",    "🚫"),
}

# ---------------------------------------------------------------------------
# Memory helpers
# ---------------------------------------------------------------------------

def write_memory(entry: Dict[str, Any]):
    entry["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def search_memory(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    if not MEMORY_FILE.exists():
        return []
    q = query.lower()
    results = []
    with open(MEMORY_FILE, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if q in json.dumps(entry, ensure_ascii=False).lower():
                    results.append(entry)
            except Exception:
                pass
    return results[-limit:]


def get_all_contracts() -> List[Dict[str, Any]]:
    if not MEMORY_FILE.exists():
        return []
    contracts = []
    with open(MEMORY_FILE, encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
                if e.get("type") == "contract_analyzed":
                    contracts.append(e)
            except Exception:
                pass
    return contracts


def file_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def dispatch_tool(name: str, inp: Dict[str, Any]) -> str:

    # ── read_contract ─────────────────────────────────────────────────────────
    if name == "read_contract":
        path = inp.get("path", "")
        try:
            content = Path(path).read_text(encoding="utf-8", errors="replace")
            words   = len(content.split())
            clauses = content.count("\n\n")

            # Detect language
            turkish_indicators = ["madde", "sözleşme", "taraf", "işbu", "yüklenici",
                                   "hizmet", "ücret", "fesih", "gizlilik", "rekabet"]
            text_lower = content.lower()
            lang = "TR" if sum(1 for w in turkish_indicators if w in text_lower) >= 3 else "EN"

            return (
                f"CONTRACT LOADED | Language: {lang} | {words} words | ~{clauses} sections\n\n"
                + content[:6000]
            )
        except FileNotFoundError:
            return f"Error: File not found: {path}"
        except Exception as e:
            return f"Error reading file: {e}"

    # ── detect_language ───────────────────────────────────────────────────────
    elif name == "detect_language":
        text = inp.get("text", "").lower()
        turkish_words = ["madde", "sözleşme", "taraf", "işbu", "yüklenici",
                         "hizmet", "ücret", "fesih", "gizlilik"]
        score = sum(1 for w in turkish_words if w in text)
        lang = "TR" if score >= 3 else "EN"
        return f"Detected language: {lang} (confidence score: {score})"

    # ── search_memory ─────────────────────────────────────────────────────────
    elif name == "search_memory":
        query   = inp.get("query", "")
        results = search_memory(query)
        if not results:
            return f"No prior contracts found matching '{query}'."
        lines = []
        for r in results:
            ct      = r.get("contract_type", "Unknown")
            parties = r.get("parties", "?")
            risk    = r.get("risk_level", "?")
            verdict = r.get("verdict", "?")
            date    = r.get("timestamp", "?")[:10]
            lines.append(f"[{date}] {ct} - {parties} - Risk: {risk} - Verdict: {verdict}")
        return f"Found {len(results)} related contract(s):\n" + "\n".join(lines)

    # ── score_clause ──────────────────────────────────────────────────────────
    elif name == "score_clause":
        clause_name = inp.get("clause_name", "")
        score       = inp.get("score", 0)
        reason      = inp.get("reason", "")
        finding     = inp.get("finding", "")
        is_red_flag = inp.get("is_red_flag", False)
        negotiation = inp.get("negotiation_suggestion", "")

        risk = ("CRITICAL" if score >= 8 else "HIGH" if score >= 5
                else "MEDIUM" if score >= 3 else "LOW")
        icon = "🚨" if is_red_flag else RISK_ICONS.get(risk, "")

        result = f"{icon} {clause_name}: {score}/10"
        if reason:
            result += f"\n   Reason: {reason}"
        if finding:
            result += f"\n   Finding: {finding}"
        if negotiation:
            result += f"\n   💬 Suggest: {negotiation}"
        if is_red_flag:
            result += "\n   ⚠️  RED FLAG - requires immediate attention"
        return result

    # ── check_missing_clauses ─────────────────────────────────────────────────
    elif name == "check_missing_clauses":
        contract_type   = inp.get("contract_type", "")
        present_clauses = [c.lower() for c in inp.get("present_clauses", [])]

        standard_clauses = {
            "Freelance Service Agreement": [
                "payment terms", "intellectual property", "confidentiality",
                "termination", "non-compete", "dispute resolution",
                "governing law", "liability", "warranties"
            ],
            "Employment Agreement": [
                "compensation", "benefits", "intellectual property", "confidentiality",
                "non-compete", "non-solicitation", "termination", "at-will",
                "dispute resolution", "governing law"
            ],
            "NDA": [
                "definition of confidential information", "obligations",
                "exclusions", "term", "return of information",
                "remedies", "governing law"
            ],
            "Service Agreement": [
                "scope of services", "payment", "term", "termination",
                "liability", "warranties", "confidentiality", "governing law"
            ],
        }

        expected = standard_clauses.get(contract_type, [])
        missing  = []
        for clause in expected:
            if not any(clause in p for p in present_clauses):
                missing.append(clause)

        if not missing:
            return f"All standard clauses present for {contract_type}."
        return (
            f"Missing {len(missing)} standard clause(s) for {contract_type}:\n"
            + "\n".join(f"  - {m}" for m in missing)
            + "\n\nRecommend adding these clauses before signing."
        )

    # ── generate_negotiation_text ─────────────────────────────────────────────
    elif name == "generate_negotiation_text":
        clause_name = inp.get("clause_name", "")
        issue       = inp.get("issue", "")
        language    = inp.get("language", "EN")
        current     = inp.get("current_text", "")

        # Store negotiation suggestion in memory
        write_memory({
            "type":        "negotiation_suggestion",
            "clause":      clause_name,
            "issue":       issue,
            "language":    language,
        })

        if language == "TR":
            return (
                f"📝 '{clause_name}' maddesi için müzakere önerisi:\n\n"
                f"Mevcut sorun: {issue}\n\n"
                f"Önerilen değişiklik: Bu maddenin her iki tarafın haklarını dengeli şekilde "
                f"koruyan, makul süreler ve kapsamlar içeren bir versiyonuyla değiştirilmesi önerilir. "
                f"Avukatınıza danışarak belirli değişiklikler talep edin."
            )
        return (
            f"📝 Negotiation suggestion for '{clause_name}':\n\n"
            f"Issue: {issue}\n\n"
            f"Suggested approach: Request a revised version of this clause that provides "
            f"balanced protections for both parties, with reasonable timeframes and scope. "
            f"Consult your attorney for specific replacement language."
        )

    # ── compare_contracts ─────────────────────────────────────────────────────
    elif name == "compare_contracts":
        party    = inp.get("party", "")
        ctype    = inp.get("contract_type", "")
        current  = inp.get("current_terms", {})
        prior    = search_memory(f"{party} {ctype}")

        if not prior:
            return f"No prior contracts from '{party}'. This is the first analysis - baseline established."

        latest = prior[-1]
        lines  = [
            f"Found {len(prior)} prior contract(s) from '{party}':",
            f"  Last analyzed: {latest.get('timestamp','?')[:10]}",
            f"  Previous risk: {latest.get('risk_level','?')}",
            f"  Previous verdict: {latest.get('verdict','?')}",
        ]

        # Compare risk trend
        prev_risk  = latest.get("risk_level", "")
        curr_risks = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        if current.get("risk_level") and prev_risk:
            prev_val = curr_risks.get(prev_risk, 0)
            curr_val = curr_risks.get(current.get("risk_level",""), 0)
            if curr_val > prev_val:
                lines.append("  ⚠️  Terms have gotten WORSE since last contract.")
            elif curr_val < prev_val:
                lines.append("  ✅ Terms have IMPROVED since last contract.")
            else:
                lines.append("  → Risk level unchanged from previous contract.")

        return "\n".join(lines)

    # ── render_verdict ────────────────────────────────────────────────────────
    elif name == "render_verdict":
        verdict  = inp.get("verdict", "NEGOTIATE").upper()
        reason   = inp.get("reason", "")
        language = inp.get("language", "EN")

        color, icon = VERDICT_STYLES.get(verdict, ("white", "❓"))

        if language == "TR":
            labels = {
                "SIGN":      "İMZALAYABİLİRSİNİZ",
                "NEGOTIATE": "MÜZAKERE EDİN",
                "REJECT":    "İMZALAMAYIN",
            }
        else:
            labels = {
                "SIGN":      "SIGN",
                "NEGOTIATE": "NEGOTIATE FIRST",
                "REJECT":    "DO NOT SIGN",
            }

        label = labels.get(verdict, verdict)
        console.print(Panel(
            f"[{color}]{icon}  {label}[/]\n\n{reason}",
            title="[bold]Final Verdict[/]",
            border_style=color.split()[-1] if " " in color else color,
            padding=(1, 2),
            width=min(100, console.width - 4),
        ))

        write_memory({
            "type":    "verdict",
            "verdict": verdict,
            "reason":  reason[:200],
            "language": language,
        })
        return f"Verdict rendered: {verdict}"

    # ── save_report ───────────────────────────────────────────────────────────
    elif name == "save_report":
        contract_type     = inp.get("contract_type", "Unknown")
        parties           = inp.get("parties", "Unknown")
        risk_level        = inp.get("risk_level", "MEDIUM")
        verdict           = inp.get("verdict", "NEGOTIATE")
        summary           = inp.get("summary", "")
        findings          = inp.get("findings", [])
        key_terms         = inp.get("key_terms", {})
        recommendations   = inp.get("recommendations", [])
        missing_clauses   = inp.get("missing_clauses", [])
        contract_hash     = inp.get("contract_hash", "unknown")
        language          = inp.get("language", "EN")

        # Build report
        lines = [
            f"# Legal Analysis Report",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
            f"Language: {language}",
            f"",
            f"## Contract Overview",
            f"**Type:** {contract_type}",
            f"**Parties:** {parties}",
            f"**Overall Risk:** {RISK_ICONS.get(risk_level,'')} {risk_level}",
            f"**Verdict:** {VERDICT_STYLES.get(verdict,('',''))[1]} {verdict}",
            f"**Hash:** {contract_hash}",
            f"",
            f"## Executive Summary",
            summary,
            f"",
            f"## Key Findings",
        ]
        for f_item in findings:
            lines.append(f"- {f_item}")
        if missing_clauses:
            lines += ["", "## Missing Standard Clauses"]
            for m in missing_clauses:
                lines.append(f"- ⚠️  {m}")
        lines += ["", "## Key Terms"]
        for k, v in key_terms.items():
            lines.append(f"- **{k}:** {v}")
        lines += ["", "## Recommended Actions"]
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")

        report_content = "\n".join(lines)

        slug        = contract_type.lower().replace(" ", "_")[:20]
        ts          = time.strftime("%Y%m%d_%H%M%S")
        report_path = REPORTS_DIR / f"{ts}_{slug}.md"
        report_path.write_text(report_content, encoding="utf-8")

        # Archive to memory
        write_memory({
            "type":          "contract_analyzed",
            "contract_type": contract_type,
            "parties":       parties,
            "risk_level":    risk_level,
            "verdict":       verdict,
            "contract_hash": contract_hash,
            "language":      language,
            "findings_count": len(findings),
            "report_path":   str(report_path),
        })

        # Display in terminal
        risk_color = RISK_COLORS.get(risk_level, "white")
        risk_icon  = RISK_ICONS.get(risk_level, "")

        console.print(Rule("[bold]Legal Analysis Report[/]"))

        t = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
        t.add_column("Field", style="dim", width=22)
        t.add_column("Value")
        t.add_row("Contract Type",  contract_type)
        t.add_row("Parties",        parties)
        t.add_row("Language",       language)
        t.add_row("Overall Risk",   Text(f"{risk_icon} {risk_level}", style=risk_color))
        t.add_row("Verdict",        Text(f"{VERDICT_STYLES.get(verdict,('','❓'))[1]} {verdict}",
                                         style=VERDICT_STYLES.get(verdict,("white",""))[0]))
        t.add_row("Findings",       str(len(findings)))
        t.add_row("Report saved",   str(report_path))
        console.print(t)

        if findings:
            console.print(f"\n[bold red]Key Findings:[/]")
            for f_item in findings:
                console.print(f"  • {f_item}")

        if missing_clauses:
            console.print(f"\n[bold yellow]Missing Clauses:[/]")
            for m in missing_clauses:
                console.print(f"  ⚠️  {m}")

        if key_terms:
            console.print(f"\n[bold cyan]Key Terms:[/]")
            kt = Table(box=box.SIMPLE, show_header=True, header_style="bold")
            kt.add_column("Term")
            kt.add_column("Value")
            for k, v in key_terms.items():
                kt.add_row(k, str(v))
            console.print(kt)

        if recommendations:
            console.print(f"\n[bold green]Recommended Actions:[/]")
            for i, rec in enumerate(recommendations, 1):
                console.print(f"  {i}. {rec}")

        return f"Report saved: {report_path}"

    # ── send_alert ────────────────────────────────────────────────────────────
    elif name == "send_alert":
        risk_level = inp.get("risk_level", "HIGH")
        message    = inp.get("message", "")
        language   = inp.get("language", "EN")

        color = RISK_COLORS.get(risk_level, "white")
        icon  = RISK_ICONS.get(risk_level, "⚠️")

        if language == "TR":
            title = "⚠️  Hukuki Uyarı"
        else:
            title = "⚠️  Legal Alert"

        console.print(Panel(
            f"[{color}]{icon} ALERT - {risk_level} RISK[/]\n\n{message}",
            title=f"[bold red]{title}[/]",
            border_style="red",
            width=min(100, console.width - 4),
        ))
        write_memory({"type": "alert_sent", "risk_level": risk_level,
                      "message": message[:200], "language": language})
        return f"Alert sent: {risk_level}"

    return f"Unknown tool: {name}"

# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

TOOLS = [
    {"type": "function", "function": {
        "name": "read_contract",
        "description": "Read and load a contract file. Also detects language automatically.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
        }, "required": ["path"]}}},

    {"type": "function", "function": {
        "name": "detect_language",
        "description": "Detect if the contract is in English or Turkish.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "Contract text sample"},
        }, "required": ["text"]}}},

    {"type": "function", "function": {
        "name": "search_memory",
        "description": "Search previously analyzed contracts for the same counter-party.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
        }, "required": ["query"]}}},

    {"type": "function", "function": {
        "name": "score_clause",
        "description": "Score a clause for risk (1-10) and suggest negotiation language.",
        "parameters": {"type": "object", "properties": {
            "clause_name":           {"type": "string"},
            "score":                 {"type": "integer"},
            "reason":                {"type": "string"},
            "finding":               {"type": "string"},
            "is_red_flag":           {"type": "boolean"},
            "negotiation_suggestion":{"type": "string", "description": "Brief suggestion to improve this clause"},
        }, "required": ["clause_name", "score", "reason"]}}},

    {"type": "function", "function": {
        "name": "check_missing_clauses",
        "description": "Check if standard clauses are missing from the contract.",
        "parameters": {"type": "object", "properties": {
            "contract_type":   {"type": "string"},
            "present_clauses": {"type": "array", "items": {"type": "string"}},
        }, "required": ["contract_type", "present_clauses"]}}},

    {"type": "function", "function": {
        "name": "generate_negotiation_text",
        "description": "Generate specific negotiation language for a problematic clause.",
        "parameters": {"type": "object", "properties": {
            "clause_name":  {"type": "string"},
            "issue":        {"type": "string"},
            "current_text": {"type": "string"},
            "language":     {"type": "string", "description": "EN or TR"},
        }, "required": ["clause_name", "issue"]}}},

    {"type": "function", "function": {
        "name": "compare_contracts",
        "description": "Compare with prior contracts from the same party.",
        "parameters": {"type": "object", "properties": {
            "party":         {"type": "string"},
            "contract_type": {"type": "string"},
            "current_terms": {"type": "object"},
        }, "required": ["party", "contract_type"]}}},

    {"type": "function", "function": {
        "name": "render_verdict",
        "description": "Render the final SIGN / NEGOTIATE / REJECT verdict.",
        "parameters": {"type": "object", "properties": {
            "verdict":  {"type": "string", "description": "SIGN, NEGOTIATE, or REJECT"},
            "reason":   {"type": "string", "description": "One sentence explaining the verdict"},
            "language": {"type": "string", "description": "EN or TR"},
        }, "required": ["verdict", "reason"]}}},

    {"type": "function", "function": {
        "name": "save_report",
        "description": "Save the complete analysis report. Call this LAST.",
        "parameters": {"type": "object", "properties": {
            "contract_type":   {"type": "string"},
            "parties":         {"type": "string"},
            "risk_level":      {"type": "string"},
            "verdict":         {"type": "string", "description": "SIGN / NEGOTIATE / REJECT"},
            "summary":         {"type": "string"},
            "findings":        {"type": "array", "items": {"type": "string"}},
            "key_terms":       {"type": "object"},
            "recommendations": {"type": "array", "items": {"type": "string"}},
            "missing_clauses": {"type": "array", "items": {"type": "string"}},
            "contract_hash":   {"type": "string"},
            "language":        {"type": "string"},
        }, "required": ["contract_type", "parties", "risk_level", "verdict",
                        "summary", "findings", "key_terms", "recommendations"]}}},

    {"type": "function", "function": {
        "name": "send_alert",
        "description": "Send a risk alert for CRITICAL or HIGH contracts.",
        "parameters": {"type": "object", "properties": {
            "risk_level": {"type": "string"},
            "message":    {"type": "string"},
            "language":   {"type": "string"},
        }, "required": ["risk_level", "message"]}}},
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM = textwrap.dedent("""
    You are Hermes Legal Advisor - an expert contract analyst. You analyze contracts
    in both English and Turkish with equal depth.

    IMPORTANT: You are not providing legal advice. Always recommend consulting an attorney.

    Mandatory workflow:
    1. read_contract - load the document, note the language (EN/TR)
    2. search_memory - check for prior contracts from the same party
    3. score_clause - score ALL of these categories (one call each):
       Termination, Liability, Intellectual Property, Non-Compete,
       Confidentiality, Payment Terms, Governing Law, Auto-Renewal,
       Dispute Resolution
       For each clause, include a negotiation_suggestion when score >= 5
    4. check_missing_clauses - identify missing standard clauses
    5. generate_negotiation_text - for the 2-3 most critical clauses
    6. compare_contracts - compare with prior versions if memory has them
    7. send_alert - ONLY if CRITICAL or HIGH overall risk
    8. render_verdict - give SIGN / NEGOTIATE / REJECT with one-sentence reason
    9. save_report - compile everything into the final structured report

    Scoring:
    - 1-3: Standard and acceptable
    - 4-6: Somewhat unfavorable, worth noting
    - 7-8: Significantly unfavorable, recommend negotiation
    - 9-10: Red flag, potentially unacceptable

    Verdict logic:
    - SIGN: Overall risk LOW, no critical clauses
    - NEGOTIATE: Some HIGH/CRITICAL clauses but fixable
    - REJECT: Multiple CRITICAL clauses or fundamental deal-breakers

    If contract is in Turkish, respond in Turkish in all text fields.
    Always cite specific clause language in your findings.
""").strip()

# ---------------------------------------------------------------------------
# Sample Turkish contract
# ---------------------------------------------------------------------------

TURKISH_CONTRACT = """SERBEST ÇALIŞMA HİZMET SÖZLEŞMESİ

Bu Sözleşme, 1 Ocak 2026 tarihinde TechCorp A.Ş. ("Müşteri") ile aşağıda
belirtilen kişi ("Yüklenici") arasında akdedilmiştir.

1. HİZMETLER
Yüklenici, Müşterinin talep ettiği yazılım geliştirme hizmetlerini sunmayı
kabul eder.

2. ÜCRET
Müşteri, Yükleniciye saatlik 500 TL ödeme yapacaktır. Faturalar teslimden
itibaren 90 gün içinde ödenecektir.

3. FİKRİ MÜLKİYET
Yüklenici tarafından bu Sözleşme kapsamında oluşturulan tüm çalışmalar,
çalışma saatleri dışında oluşturulanlar dahil, Müşteriye ait olacaktır.

4. GİZLİLİK
Yüklenici, Müşteriden aldığı tüm bilgileri gizli tutacak ve bu yükümlülük
Sözleşmenin sona ermesinden sonra süresiz olarak devam edecektir.

5. REKABET YASAĞI
Sözleşme süresince ve sona ermesinden sonraki BEŞ (5) YIL boyunca, Yüklenici
dünya genelinde Müşteriyle rekabet eden herhangi bir faaliyette bulunamaz.

6. FESİH
Müşteri bu Sözleşmeyi istediği zaman, herhangi bir sebep olmaksızın,
1 GÜN önceden yazılı bildirimle feshedebilir.

7. SORUMLULUK
Yüklenicinin sorumluluğu sınırsızdır. Müşterinin sorumluluğu son 7 günde
ödenen tutarla sınırlıdır.

8. UYGULANACAK HUKUK
Bu Sözleşme Delaware Hukukuna tabidir.

Yüklenici: ____________________  Tarih: ____________________
"""

# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

# Model options:
# nousresearch/hermes-3-llama-3.1-405b  - Hermes 3 (recommended, requires credits)
# google/gemini-2.0-flash-001           - Fast, excellent tool calling
# openrouter/auto                        - Auto-select
DEFAULT_MODEL = "nousresearch/hermes-3-llama-3.1-405b"


def run_legal_analysis(contract_path: str, api_key: str,
                       model: str = DEFAULT_MODEL,
                       max_turns: int = 30) -> Dict[str, Any]:

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/Lethe044/hermes-legal",
            "X-Title": "Hermes Legal Advisor",
        },
    )

    contract_name = Path(contract_path).name
    contract_hash_val = ""
    try:
        text = Path(contract_path).read_text(encoding="utf-8", errors="replace")
        contract_hash_val = file_hash(text)
    except Exception:
        pass

    prompt = textwrap.dedent(f"""
        Analyze this contract: {contract_path}
        Hash: {contract_hash_val}

        Full pipeline:
        1. Read the contract and detect language
        2. Search memory for prior contracts from same party
        3. Score all 9 clause categories - include negotiation suggestions for risky clauses
        4. Check for missing standard clauses
        5. Generate negotiation text for the 2-3 most critical issues
        6. Compare with prior contracts if available
        7. Send alert if CRITICAL or HIGH risk
        8. Render final SIGN / NEGOTIATE / REJECT verdict
        9. Save complete report

        Be thorough. Cite exact clause language. The person may sign this tomorrow.
    """).strip()

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user",   "content": prompt},
    ]

    turn          = 0
    calls: List[str] = []
    clause_scores: Dict[str, int] = {}
    start         = time.time()
    report_saved  = 0
    alerts_sent   = 0
    verdict_shown = 0

    console.print(Panel(
        "[bold cyan]Hermes Legal Advisor[/]\n"
        "[dim]Autonomous contract risk analysis[/]",
        border_style="cyan",
    ))
    console.print(Rule(f"[bold]Analyzing: {contract_name}[/]"))
    console.print(f"[dim]Hash: {contract_hash_val} | Model: {model}[/]\n")

    while turn < max_turns:
        turn += 1

        with Progress(SpinnerColumn("dots"),
                      TextColumn(f"[cyan]Analyzing... turn {turn}/{max_turns}[/]"),
                      transient=True, console=console) as p:
            p.add_task("")
            resp = client.chat.completions.create(
                model=model, messages=messages,
                tools=TOOLS, tool_choice="auto", max_tokens=2000,
            )

        msg = resp.choices[0].message

        if msg.content and msg.content.strip() and len(msg.content.strip()) < 400:
            console.print(Panel(msg.content.strip(),
                                title="[green]Hermes[/]", border_style="green",
                                width=min(100, console.width - 4)))

        if not msg.tool_calls or resp.choices[0].finish_reason == "stop":
            if report_saved == 0 and turn < max_turns - 1:
                messages.append({"role": "user", "content":
                    "Please call render_verdict and then save_report now to complete the analysis."})
                continue
            break

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })

        # Split tool calls: score_clause runs concurrently, others sequentially
        icons = {
            "read_contract":             "📄",
            "detect_language":           "🌐",
            "search_memory":             "🔍",
            "score_clause":              "⚖️ ",
            "check_missing_clauses":     "🔎",
            "generate_negotiation_text": "💬",
            "compare_contracts":         "📊",
            "render_verdict":            "🏛️ ",
            "save_report":               "💾",
            "send_alert":                "🚨",
        }

        score_tcs    = [tc for tc in msg.tool_calls if tc.function.name == "score_clause"]
        non_score_tcs = [tc for tc in msg.tool_calls if tc.function.name != "score_clause"]

        # --- Concurrent execution for score_clause ---
        if score_tcs:
            def _run_score(tc):
                try:
                    tinp = json.loads(tc.function.arguments)
                except Exception:
                    tinp = {}
                result = dispatch_tool("score_clause", tinp)
                return tc, tinp, result

            if len(score_tcs) > 1:
                console.print(
                    f"  [dim cyan]⚡ Running {len(score_tcs)} clause scores concurrently...[/]"
                )
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(score_tcs)) as ex:
                futures = {ex.submit(_run_score, tc): tc for tc in score_tcs}
                score_results = []
                for fut in concurrent.futures.as_completed(futures):
                    tc, tinp, result = fut.result()
                    score_results.append((tc, tinp, result))

            # Display and collect results in original order
            for tc in score_tcs:
                match = next((r for r in score_results if r[0].id == tc.id), None)
                if not match:
                    continue
                _, tinp, result = match
                calls.append("score_clause")
                cname = tinp.get("clause_name", "")
                score = tinp.get("score", 0)
                clause_scores[cname] = score
                risk  = ("CRITICAL" if score >= 8 else "HIGH" if score >= 5
                         else "MEDIUM" if score >= 3 else "LOW")
                color = RISK_COLORS.get(risk, "white")
                icon  = RISK_ICONS.get(risk, "")
                neg   = tinp.get("negotiation_suggestion", "")
                console.print(
                    f"  ⚖️  [yellow]score_clause[/] "
                    f"[dim]{cname}[/] → [{color}]{icon} {score}/10 ({risk})[/]"
                )
                if neg and score >= 5:
                    console.print(f"     [dim]💬 {neg[:80]}[/]")
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        # --- Sequential execution for all other tools ---
        for tc in non_score_tcs:
            tname = tc.function.name
            try:
                tinp = json.loads(tc.function.arguments)
            except Exception:
                tinp = {}
            calls.append(tname)

            if tname == "render_verdict":
                verdict_shown += 1
                console.print(f"  🏛️  [yellow]render_verdict[/] [dim]{tinp.get('verdict','')}[/]")
            else:
                preview = str(tinp.get("path", tinp.get("query",
                              tinp.get("clause_name", tinp.get("contract_type",
                              tinp.get("message", tinp.get("verdict", "")))))))[:70]
                console.print(f"  {icons.get(tname,'🔧')} [yellow]{tname}[/] [dim]{preview}[/]")

            result = dispatch_tool(tname, tinp)

            if tname == "save_report":
                report_saved += 1
            elif tname == "send_alert":
                alerts_sent += 1
            elif tname == "render_verdict":
                pass
            elif tname not in ("read_contract",):
                if len(result) < 500:
                    console.print(f"  [dim]{result}[/]")

            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    elapsed = time.time() - start

    # Clause risk summary table
    if clause_scores:
        console.print(Rule("[bold]Clause Risk Summary[/]"))
        ct = Table(box=box.ROUNDED, header_style="bold cyan")
        ct.add_column("Clause", style="dim")
        ct.add_column("Score")
        ct.add_column("Risk Level")
        for clause, score in sorted(clause_scores.items(), key=lambda x: -x[1]):
            risk  = ("CRITICAL" if score >= 8 else "HIGH" if score >= 5
                     else "MEDIUM" if score >= 3 else "LOW")
            color = RISK_COLORS.get(risk, "white")
            icon  = RISK_ICONS.get(risk, "")
            ct.add_row(clause, f"{score}/10", Text(f"{icon} {risk}", style=color))
        console.print(ct)

    # Session summary
    console.print(Rule("[bold green]Analysis Complete[/]"))
    st = Table(header_style="bold cyan", box=box.ROUNDED)
    st.add_column("Metric", style="dim")
    st.add_column("Value")
    for row in [
        ("Contract",       contract_name),
        ("Model",          model),
        ("Turns",          str(turn)),
        ("Tool calls",     str(len(calls))),
        ("Clauses scored", str(len(clause_scores))),
        ("Alerts sent",    str(alerts_sent)),
        ("Verdict given",  "Yes" if verdict_shown else "No"),
        ("Report saved",   "Yes" if report_saved else "No"),
        ("Elapsed",        f"{elapsed:.1f}s"),
        ("Reports dir",    str(REPORTS_DIR)),
    ]:
        st.add_row(*row)
    console.print(st)

    return {"turns": turn, "calls": len(calls),
            "clauses": len(clause_scores), "elapsed": elapsed,
            "report_saved": report_saved}



# ---------------------------------------------------------------------------
# Contract comparison mode
# ---------------------------------------------------------------------------

COMPARE_SYSTEM = (
    "You are Hermes Legal Advisor. Compare two versions of the same contract. "
    "Identify what improved, what got worse, and what stayed the same. "
    "Score each changed clause twice: once for V1 (clause_name ending in [V1]) "
    "and once for V2 (clause_name ending in [V2]). "
    "Then call render_verdict with overall assessment and save_report with summary. "
    "Respond in the same language as the contracts."
)


def run_comparison(path_v1: str, path_v2: str, api_key: str,
                   model: str = DEFAULT_MODEL, max_turns: int = 20) -> None:
    """Compare two contract versions and highlight changes."""

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/Lethe044/hermes-legal",
            "X-Title": "Hermes Legal Advisor",
        },
    )

    try:
        text_v1 = Path(path_v1).read_text(encoding="utf-8", errors="replace")
        text_v2 = Path(path_v2).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError as e:
        console.print(f"[red]File not found: {e}[/]")
        return

    console.print(Panel(
        "[bold cyan]Hermes Legal Advisor - Contract Comparison[/]\n"
        "[dim]Analyzing what changed between two versions[/]",
        border_style="cyan",
    ))
    console.print(Rule(
        f"[bold]Comparing: {Path(path_v1).name} vs {Path(path_v2).name}[/]"
    ))
    console.print(f"[dim]Model: {model}[/]\n")

    prompt = (
        f"Compare these two contract versions and identify all changes.\n\n"
        f"VERSION 1 ({Path(path_v1).name}):\n{text_v1[:3000]}\n\n"
        f"VERSION 2 ({Path(path_v2).name}):\n{text_v2[:3000]}\n\n"
        "For each clause that changed:\n"
        "1. Call score_clause for V1 version (clause_name ending in ' [V1]')\n"
        "2. Call score_clause for V2 version (clause_name ending in ' [V2]')\n"
        "3. Note if it improved or got worse\n\n"
        "Then:\n"
        "- Call render_verdict: is V2 better, worse, or mixed?\n"
        "- Call save_report with a comparison summary\n\n"
        "Be thorough. Every changed clause should be scored twice."
    )

    messages = [
        {"role": "system", "content": COMPARE_SYSTEM},
        {"role": "user",   "content": prompt},
    ]

    turn = 0
    calls: List[str] = []
    clause_scores: Dict[str, int] = {}
    start = time.time()
    report_saved = 0

    while turn < max_turns:
        turn += 1
        with Progress(SpinnerColumn("dots"),
                      TextColumn(f"[cyan]Comparing... turn {turn}/{max_turns}[/]"),
                      transient=True, console=console) as p:
            p.add_task("")
            resp = client.chat.completions.create(
                model=model, messages=messages,
                tools=TOOLS, tool_choice="auto", max_tokens=2000,
            )

        msg = resp.choices[0].message
        if msg.content and msg.content.strip() and len(msg.content.strip()) < 300:
            console.print(Panel(
                msg.content.strip(), title="[green]Hermes[/]",
                border_style="green", width=min(100, console.width - 4)
            ))

        if not msg.tool_calls or resp.choices[0].finish_reason == "stop":
            if report_saved == 0 and turn < max_turns - 1:
                messages.append({"role": "user", "content":
                    "Please call render_verdict and save_report now to complete the comparison."
                })
                continue
            break

        messages.append({
            "role": "assistant", "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            tname = tc.function.name
            try:
                tinp = json.loads(tc.function.arguments)
            except Exception:
                tinp = {}
            calls.append(tname)

            if tname == "score_clause":
                cname = tinp.get("clause_name", "")
                score = tinp.get("score", 0)
                clause_scores[cname] = score
                risk  = ("CRITICAL" if score >= 8 else "HIGH" if score >= 5
                         else "MEDIUM" if score >= 3 else "LOW")
                color = RISK_COLORS.get(risk, "white")
                icon  = RISK_ICONS.get(risk, "")
                if "[V1]" in cname:
                    tag_color = "dim red"
                elif "[V2]" in cname:
                    tag_color = "dim green"
                else:
                    tag_color = "dim"
                console.print(
                    f"  ⚖️  [{tag_color}]{cname}[/] "
                    f"→ [{color}]{icon} {score}/10 ({risk})[/]"
                )
            elif tname == "render_verdict":
                console.print(
                    f"  🏛️  [yellow]render_verdict[/] [dim]{tinp.get('verdict','')}[/]"
                )
            elif tname == "save_report":
                report_saved += 1
                console.print(f"  💾 [yellow]save_report[/]")
            else:
                preview = str(tinp.get("path", tinp.get("query",
                              tinp.get("message", ""))))[:60]
                console.print(f"  🔧 [yellow]{tname}[/] [dim]{preview}[/]")

            result = dispatch_tool(tname, tinp)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    elapsed = time.time() - start

    # Comparison table
    if clause_scores:
        console.print(Rule("[bold]Clause Comparison[/]"))
        ct = Table(box=box.ROUNDED, header_style="bold cyan")
        ct.add_column("Clause")
        ct.add_column("V1 → V2")
        ct.add_column("Risk (V2)")
        ct.add_column("Change")

        v1_map = {
            k.replace(" [V1]", "").replace(" [V2]", ""): v
            for k, v in clause_scores.items() if "[V1]" in k
        }
        v2_map = {
            k.replace(" [V1]", "").replace(" [V2]", ""): v
            for k, v in clause_scores.items() if "[V2]" in k
        }

        for clause in sorted(set(list(v1_map.keys()) + list(v2_map.keys()))):
            s1 = v1_map.get(clause)
            s2 = v2_map.get(clause)
            if s1 is not None and s2 is not None:
                if s2 < s1:
                    change = Text("↓ Improved", style="green")
                elif s2 > s1:
                    change = Text("↑ Got worse", style="red")
                else:
                    change = Text("→ Unchanged", style="dim")
                risk2  = ("CRITICAL" if s2 >= 8 else "HIGH" if s2 >= 5
                          else "MEDIUM" if s2 >= 3 else "LOW")
                color2 = RISK_COLORS.get(risk2, "white")
                icon2  = RISK_ICONS.get(risk2, "")
                ct.add_row(
                    clause,
                    f"{s1} → {s2}/10",
                    Text(f"{icon2} {risk2}", style=color2),
                    change,
                )
        console.print(ct)

    console.print(Rule("[bold green]Comparison Complete[/]"))
    console.print(f"[dim]Elapsed: {elapsed:.1f}s | Tool calls: {len(calls)}[/]")


# ---------------------------------------------------------------------------
# Watch mode (Cron-style folder monitoring)
# ---------------------------------------------------------------------------

def run_watch_mode(folder: str, api_key: str,
                   model: str = DEFAULT_MODEL, max_turns: int = 25) -> None:
    """Watch a folder for new .txt contract files and auto-analyze them."""
    import hashlib as _hashlib

    watch_path = Path(folder)
    if not watch_path.exists():
        watch_path.mkdir(parents=True)

    processed_file = LEGAL_DIR / "watched_files.json"
    processed: Dict[str, Any] = {}
    if processed_file.exists():
        try:
            processed = json.loads(processed_file.read_text(encoding="utf-8"))
        except Exception:
            processed = {}

    console.print(Panel(
        "[bold cyan]Hermes Legal Advisor - Watch Mode[/]\n"
        f"[dim]Monitoring: {watch_path.absolute()}\n"
        "Drop any .txt contract file into this folder.\n"
        "Hermes will automatically analyze it.\n"
        "Press Ctrl+C to stop.[/]",
        border_style="cyan",
    ))
    console.print(f"\n[dim]Watching {watch_path.absolute()} ...[/]")
    console.print(f"[dim]Already processed: {len(processed)} file(s)[/]\n")

    try:
        while True:
            for f in watch_path.glob("*.txt"):
                fhash = _hashlib.md5(f.read_bytes()).hexdigest()[:12]
                if fhash not in processed:
                    console.print(
                        f"\n[bold green]📄 New contract detected: {f.name}[/]"
                    )
                    console.print("[dim]Starting automatic analysis...[/]\n")
                    try:
                        run_legal_analysis(str(f), api_key, model, max_turns)
                        processed[fhash] = {
                            "file": f.name,
                            "analyzed_at": time.strftime(
                                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                            ),
                        }
                        processed_file.write_text(
                            json.dumps(processed, indent=2, ensure_ascii=False),
                            encoding="utf-8",
                        )
                        console.print(
                            f"\n[green]Analyzed and archived: {f.name}[/]"
                        )
                        console.print("[dim]Watching for more files...[/]\n")
                    except Exception as e:
                        console.print(f"[red]Error analyzing {f.name}: {e}[/]")

            time.sleep(3)

    except KeyboardInterrupt:
        console.print(
            f"\n[dim]Watch mode stopped. "
            f"Analyzed {len(processed)} contract(s) total.[/]"
        )



# ---------------------------------------------------------------------------
# Chat mode
# ---------------------------------------------------------------------------

def run_chat_mode(api_key: str, model: str = DEFAULT_MODEL):
    """Interactive chat - ask questions about contracts or past analyses."""

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/Lethe044/hermes-legal",
            "X-Title": "Hermes Legal Advisor",
        },
    )

    console.print(Panel(
        "[bold cyan]Hermes Legal Advisor - Chat Mode[/]\n"
        "[dim]Ask about contract clauses, past analyses, or legal concepts.\n"
        "Type 'exit' to leave.[/]",
        border_style="cyan",
    ))

    # Load memory context to inject into system prompt
    all_contracts = get_all_contracts()
    memory_context = ""
    if all_contracts:
        memory_context = "\n\nContracts you have previously analyzed:\n"
        for c in all_contracts[-10:]:
            memory_context += (
                f"- [{c.get('timestamp','?')[:10]}] "
                f"{c.get('contract_type','?')} | "
                f"Parties: {c.get('parties','?')} | "
                f"Risk: {c.get('risk_level','?')} | "
                f"Verdict: {c.get('verdict','?')}\n"
            )
        memory_context += "\nUse this context to answer questions about past analyses."

    chat_system = (
        "You are Hermes Legal Advisor in conversational mode. "
        "You have analyzed contracts before and remember them. "
        "ALWAYS call search_memory tool when the user asks about past contracts, "
        "specific parties, or previous analyses - even if you think you know the answer. "
        "Respond in the same language the user writes in (EN or TR). "
        "Keep answers clear and practical. Always recommend consulting an attorney."
        + memory_context
    )

    messages = [{"role": "system", "content": chat_system}]

    while True:
        try:
            user_input = input("\n[You]: ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/]")
            break

        if user_input.lower() in ("exit", "quit", "bye", "görüşürüz", "çıkış", "q"):
            console.print("[dim]Goodbye! / Görüşürüz![/]")
            return
        if not user_input:
            continue

        # Auto-search memory for contract/party related questions
        memory_keywords = ["contract", "analyzed", "before", "previous", "techcorp",
                           "sign", "safe", "risk", "verdict", "sözleşme", "analiz",
                           "daha önce", "geçmiş", "inceledi"]
        should_search = any(kw in user_input.lower() for kw in memory_keywords)

        if should_search:
            # Pre-fetch memory and inject as context
            mem_results = search_memory(user_input, limit=5)
            if mem_results:
                mem_text = "\n\nRelevant memory entries:\n" + "\n".join(
                    json.dumps(r, ensure_ascii=False) for r in mem_results
                )
                enriched = user_input + mem_text
            else:
                enriched = user_input
            messages.append({"role": "user", "content": enriched})
        else:
            messages.append({"role": "user", "content": user_input})

        with Progress(SpinnerColumn("dots"),
                      TextColumn("[cyan]Thinking...[/]"),
                      transient=True, console=console) as p:
            p.add_task("")
            resp = client.chat.completions.create(
                model=model, messages=messages,
                tools=[TOOLS[2]],  # search_memory in chat
                tool_choice="auto", max_tokens=1000,
            )

        msg = resp.choices[0].message

        # Handle tool calls
        if msg.tool_calls:
            messages.append({
                "role": "assistant", "content": msg.content or "",
                "tool_calls": [{"id": tc.id, "type": "function",
                                "function": {"name": tc.function.name,
                                             "arguments": tc.function.arguments}}
                               for tc in msg.tool_calls],
            })
            for tc in msg.tool_calls:
                try:
                    tinp = json.loads(tc.function.arguments)
                except Exception:
                    tinp = {}
                result = dispatch_tool(tc.function.name, tinp)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

            # Get final response
            resp2 = client.chat.completions.create(
                model=model, messages=messages, max_tokens=800)
            final = resp2.choices[0].message.content or ""
            messages.append({"role": "assistant", "content": final})
        else:
            final = msg.content or ""
            messages.append({"role": "assistant", "content": final})

        if final:
            console.print(Panel(
                Markdown(final),
                title="[green]Hermes[/]",
                border_style="green",
                width=min(100, console.width - 4),
            ))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Hermes Legal Advisor")
    parser.add_argument("--contract",  help="Path to contract file (.txt)", default=None)
    parser.add_argument("--compare-v1", dest="compare_v1", default=None,
                        help="First contract for comparison")
    parser.add_argument("--compare-v2", dest="compare_v2", default=None,
                        help="Second contract for comparison")
    parser.add_argument("--watch",     help="Watch a folder for new contracts and auto-analyze")
    parser.add_argument("--chat",      action="store_true", help="Interactive chat mode")
    parser.add_argument("--turkish",   action="store_true", help="Analyze sample Turkish contract")
    parser.add_argument("--model",     default=DEFAULT_MODEL)
    parser.add_argument("--max-turns", type=int, default=30)
    args = parser.parse_args()

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        console.print("[red]Set OPENROUTER_API_KEY first.[/]")
        console.print("  Windows: set OPENROUTER_API_KEY=sk-or-...")
        sys.exit(1)

    console.print(
        "\n[dim]⚠️  Disclaimer: Hermes Legal Advisor provides contract analysis, "
        "not legal advice. Always consult a qualified attorney before signing.[/]\n"
    )

    # Chat mode
    if args.chat:
        run_chat_mode(key, args.model)
        return

    # Turkish sample contract
    if args.turkish:
        tmp = Path("sample_contracts/turkish_contract.txt")
        tmp.parent.mkdir(exist_ok=True)
        tmp.write_text(TURKISH_CONTRACT, encoding="utf-8")
        console.print(f"[dim]Turkish sample contract written to {tmp}[/]")
        run_legal_analysis(str(tmp), key, args.model, args.max_turns)
        console.print("\n[bold green]Analysis complete.[/]")
        return

    # Compare mode
    if args.compare_v1 and args.compare_v2:
        run_comparison(args.compare_v1, args.compare_v2, key, args.model, args.max_turns)
        return

    # Watch mode
    if args.watch:
        run_watch_mode(args.watch, key, args.model, args.max_turns)
        return

    # Regular contract analysis
    if not args.contract:
        console.print("[red]Provide --contract or use --chat or --turkish[/]")
        console.print("\nAvailable sample contracts:")
        for f in Path("sample_contracts").glob("*.txt"):
            console.print(f"  python demo/demo_legal.py --contract {f}")
        console.print("\nOther modes:")
        console.print("  python demo/demo_legal.py --turkish")
        console.print("  python demo/demo_legal.py --chat")
        sys.exit(1)

    if not Path(args.contract).exists():
        console.print(f"[red]File not found: {args.contract}[/]")
        sys.exit(1)

    run_legal_analysis(args.contract, key, args.model, args.max_turns)
    console.print("\n[bold green]Analysis complete.[/]")
    console.print(f"[dim]Reports: {REPORTS_DIR}[/]")


if __name__ == "__main__":
    main()
