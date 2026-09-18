from __future__ import annotations

import time
from typing import Any, Dict

from ..providers import AnalysisResult
from ..analysis.risk import RISK_ICONS, VERDICT_ICONS


def render_markdown_report(result: AnalysisResult, contract_hash: str, trend: str | None = None) -> str:
    lines = [
        "# Legal Analysis Report",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        f"Provider: {result.provider}",
        f"Language: {result.language}",
        "",
        "## Contract Overview",
        f"**Type:** {result.contract_type}",
        f"**Parties:** {result.parties}",
        f"**Overall Risk:** {RISK_ICONS.get(result.overall_risk, '')} {result.overall_risk}",
        f"**Verdict:** {VERDICT_ICONS.get(result.verdict, '')} {result.verdict}",
        f"**Hash:** {contract_hash}",
    ]
    if trend:
        lines.append(f"**Trend vs prior contract from same party:** {trend}")
    lines += ["", "## Executive Summary", result.summary or "_No summary provided._"]

    lines += ["", "## Clause-by-Clause Scoring", "", "| Clause | Score | Red Flag | Finding |", "|---|---|---|---|"]
    for c in result.clauses:
        flag = "\U0001F6A8" if c.get("is_red_flag") else ""
        finding = (c.get("finding") or "").replace("\n", " ")
        lines.append(f"| {c.get('name', '')} | {c.get('score', '')}/10 | {flag} | {finding} |")

    negotiations = [c for c in result.clauses if c.get("negotiation_suggestion")]
    if negotiations:
        lines += ["", "## Suggested Redlines"]
        for c in negotiations:
            lines.append(f"- **{c.get('name')}:** {c.get('negotiation_suggestion')}")

    if result.missing_clauses:
        lines += ["", "## Missing Standard Clauses"]
        for m in result.missing_clauses:
            lines.append(f"- \u26A0\uFE0F {m}")

    if result.key_terms:
        lines += ["", "## Key Terms"]
        for k, v in result.key_terms.items():
            lines.append(f"- **{k}:** {v}")

    lines += ["", "## Recommended Actions"]
    for i, rec in enumerate(result.recommendations, 1):
        lines.append(f"{i}. {rec}")

    lines += [
        "",
        "---",
        "_Hermes Legal Advisor provides contract analysis, not legal advice. "
        "Always consult a qualified attorney before signing any contract._",
    ]
    return "\n".join(lines)
