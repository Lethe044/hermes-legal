from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from ..providers import AnalysisResult

RISK_HEX = {"CRITICAL": "#C0392B", "HIGH": "#D35400", "MEDIUM": "#B7950B", "LOW": "#1E8449"}
VERDICT_HEX = {"SIGN": "#1E8449", "NEGOTIATE": "#B7950B", "REJECT": "#C0392B"}


def write_pdf_report(
    result: AnalysisResult,
    contract_hash: str,
    trend: Optional[str],
    out_path: str | Path,
    firm_name: Optional[str] = None,
) -> Optional[Path]:
    """
    Write a professional-looking PDF report, suitable for sending to a
    client or attaching to an email. Returns None (without raising) if
    reportlab is not installed, so PDF export stays a purely optional
    feature that never breaks the base install.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )
    except ImportError:
        return None

    out_path = Path(out_path)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("HermesTitle", parent=styles["Title"], fontSize=20, spaceAfter=4)
    h2_style = ParagraphStyle("HermesH2", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
    body_style = ParagraphStyle("HermesBody", parent=styles["BodyText"], spaceAfter=6, leading=14)
    dim_style = ParagraphStyle("HermesDim", parent=styles["BodyText"], textColor=colors.grey, fontSize=9)

    doc = SimpleDocTemplate(str(out_path), pagesize=LETTER, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    story = []

    header = firm_name or "Hermes Legal Advisor"
    story.append(Paragraph(header, title_style))
    story.append(Paragraph("Contract Analysis Report", h2_style))
    story.append(Paragraph(
        f"Generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} | "
        f"Provider: {result.provider} | Hash: {contract_hash}", dim_style
    ))
    story.append(Spacer(1, 12))

    overview_rows = [
        ["Contract Type", result.contract_type],
        ["Parties", result.parties],
        ["Language", result.language],
        ["Overall Risk", result.overall_risk],
        ["Verdict", result.verdict],
    ]
    if trend:
        overview_rows.append(["Trend", trend])
    overview_table = Table(overview_rows, colWidths=[1.6 * inch, 4.9 * inch])
    overview_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, 3), (1, 3), colors.HexColor(RISK_HEX.get(result.overall_risk, "#000000"))),
        ("TEXTCOLOR", (1, 4), (1, 4), colors.HexColor(VERDICT_HEX.get(result.verdict, "#000000"))),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
    ]))
    story.append(overview_table)

    story.append(Paragraph("Executive Summary", h2_style))
    story.append(Paragraph(result.summary or "No summary provided.", body_style))

    if result.clauses:
        story.append(Paragraph("Clause-by-Clause Scoring", h2_style))
        clause_rows = [["Clause", "Score", "Flag", "Finding"]]
        for c in result.clauses:
            clause_rows.append([
                str(c.get("name", "")),
                f"{c.get('score', '')}/10",
                "YES" if c.get("is_red_flag") else "",
                Paragraph(str(c.get("finding", "")), body_style),
            ])
        clause_table = Table(clause_rows, colWidths=[1.3 * inch, 0.6 * inch, 0.5 * inch, 4.1 * inch], repeatRows=1)
        clause_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
            ("TEXTCOLOR", (2, 1), (2, -1), colors.HexColor("#C0392B")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(clause_table)

    negotiations = [c for c in result.clauses if c.get("negotiation_suggestion")]
    if negotiations:
        story.append(Paragraph("Suggested Redlines", h2_style))
        for c in negotiations:
            story.append(Paragraph(f"<b>{c.get('name')}:</b> {c.get('negotiation_suggestion')}", body_style))

    if result.missing_clauses:
        story.append(Paragraph("Missing Standard Clauses", h2_style))
        for m in result.missing_clauses:
            story.append(Paragraph(f"- {m}", body_style))

    if result.recommendations:
        story.append(Paragraph("Recommended Actions", h2_style))
        for i, rec in enumerate(result.recommendations, 1):
            story.append(Paragraph(f"{i}. {rec}", body_style))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Hermes Legal Advisor provides contract analysis, not legal advice. "
        "Always consult a qualified attorney before signing any contract.",
        dim_style,
    ))

    doc.build(story)
    return out_path
