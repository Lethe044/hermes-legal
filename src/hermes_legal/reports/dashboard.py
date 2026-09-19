from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

RISK_COLOR = {"CRITICAL": "#e05252", "HIGH": "#e0912e", "MEDIUM": "#e0c62e", "LOW": "#4caf6a", "": "#666"}
VERDICT_COLOR = {"SIGN": "#4caf6a", "NEGOTIATE": "#e0c62e", "REJECT": "#e05252", "": "#666"}

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Hermes Legal Advisor - Batch Dashboard</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background: #0f1115; color: #e6e6e6;
         max-width: 1000px; margin: 0 auto; padding: 32px 20px; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 2px; }}
  .sub {{ color: #9aa0a6; margin-bottom: 24px; }}
  .cards {{ display: flex; gap: 16px; margin-bottom: 28px; flex-wrap: wrap; }}
  .card {{ background: #171a22; border: 1px solid #262b36; border-radius: 10px; padding: 16px 20px; min-width: 120px; }}
  .card .num {{ font-size: 1.8rem; font-weight: 700; }}
  .card .label {{ color: #9aa0a6; font-size: 0.8rem; margin-top: 2px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #262b36; font-size: 0.9rem; }}
  th {{ color: #9aa0a6; font-weight: 600; }}
  .badge {{ padding: 3px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 700; color: #0f1115; }}
  .bar-wrap {{ background: #1b1f2a; border-radius: 6px; overflow: hidden; height: 10px; width: 140px; }}
  .bar {{ height: 100%; }}
  .disclaimer {{ margin-top: 28px; color: #6b7280; font-size: 0.8rem; }}
</style>
</head>
<body>
  <h1>Batch Risk Dashboard</h1>
  <div class="sub">Generated {generated_at} | {count} contract(s) scanned</div>

  <div class="cards">
    {cards}
  </div>

  <table>
    <tr><th>File</th><th>Type</th><th>Risk</th><th>Verdict</th><th>Red Flags</th><th></th></tr>
    {rows}
  </table>

  <div class="disclaimer">
    Hermes Legal Advisor provides contract analysis, not legal advice.
    Always consult a qualified attorney before signing any contract.
  </div>
</body>
</html>
"""


def render_batch_dashboard(rows: List[Dict[str, Any]]) -> str:
    counts: Dict[str, int] = {}
    for r in rows:
        risk = r.get("overall_risk", "")
        counts[risk] = counts.get(risk, 0) + 1

    cards_html = ""
    for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        n = counts.get(level, 0)
        cards_html += (
            f'<div class="card"><div class="num" style="color:{RISK_COLOR[level]}">{n}</div>'
            f'<div class="label">{level}</div></div>'
        )

    rows_html = ""
    for r in rows:
        risk = r.get("overall_risk", "")
        verdict = r.get("verdict", "")
        flags = r.get("red_flag_count", "")
        clause_count = r.get("clause_count", 1) or 1
        pct = int((int(flags) / int(clause_count)) * 100) if str(flags).isdigit() else 0
        rows_html += (
            "<tr>"
            f"<td>{r.get('file', '')}</td>"
            f"<td>{r.get('contract_type', '')}</td>"
            f'<td><span class="badge" style="background:{RISK_COLOR.get(risk, "#666")}">{risk}</span></td>'
            f'<td><span class="badge" style="background:{VERDICT_COLOR.get(verdict, "#666")}">{verdict}</span></td>'
            f"<td>{flags}</td>"
            f'<td><div class="bar-wrap"><div class="bar" style="width:{pct}%;background:{RISK_COLOR.get(risk, "#666")}"></div></div></td>'
            "</tr>"
        )

    return TEMPLATE.format(
        generated_at=time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        count=len(rows),
        cards=cards_html,
        rows=rows_html or "<tr><td colspan=6>No contracts scanned.</td></tr>",
    )


def write_batch_dashboard(rows: List[Dict[str, Any]], out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.write_text(render_batch_dashboard(rows), encoding="utf-8")
    return out_path
