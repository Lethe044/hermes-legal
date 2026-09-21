from __future__ import annotations

import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from .dashboard import RISK_COLOR, VERDICT_COLOR

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Hermes Legal Advisor - Portfolio Dashboard</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; background: #0f1115; color: #e6e6e6;
         max-width: 1100px; margin: 0 auto; padding: 32px 20px; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 2px; }}
  h2 {{ font-size: 1.1rem; margin-top: 32px; }}
  .sub {{ color: #9aa0a6; margin-bottom: 24px; }}
  .cards {{ display: flex; gap: 16px; margin-bottom: 12px; flex-wrap: wrap; }}
  .card {{ background: #171a22; border: 1px solid #262b36; border-radius: 10px; padding: 16px 20px; min-width: 120px; }}
  .card .num {{ font-size: 1.8rem; font-weight: 700; }}
  .card .label {{ color: #9aa0a6; font-size: 0.8rem; margin-top: 2px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #262b36; font-size: 0.9rem; }}
  th {{ color: #9aa0a6; font-weight: 600; }}
  .badge {{ padding: 3px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 700; color: #0f1115; }}
  .bar-wrap {{ background: #1b1f2a; border-radius: 6px; overflow: hidden; height: 10px; width: 100%; max-width: 300px; }}
  .bar {{ height: 100%; background: #5b8def; }}
  .disclaimer {{ margin-top: 28px; color: #6b7280; font-size: 0.8rem; }}
</style>
</head>
<body>
  <h1>Portfolio Dashboard</h1>
  <div class="sub">Generated {generated_at} | {count} contract(s) analyzed all-time</div>

  <div class="cards">{cards}</div>

  <h2>Most Common Red Flags</h2>
  <table>
    <tr><th>Clause</th><th>Times Flagged</th><th></th></tr>
    {flag_rows}
  </table>

  <h2>By Counter-Party</h2>
  <table>
    <tr><th>Parties</th><th>Contracts</th><th>Highest Risk Seen</th><th>Latest Verdict</th></tr>
    {party_rows}
  </table>

  <div class="disclaimer">
    Hermes Legal Advisor provides contract analysis, not legal advice.
    Always consult a qualified attorney before signing any contract.
  </div>
</body>
</html>
"""


def build_portfolio_stats(contracts: List[Dict[str, Any]]) -> Dict[str, Any]:
    risk_counts = Counter(c.get("risk_level", "") for c in contracts)
    flag_counter: Counter = Counter()
    for c in contracts:
        for flag in c.get("flagged_clauses", []) or []:
            flag_counter[flag] += 1

    by_party: Dict[str, Dict[str, Any]] = {}
    risk_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "": 0}
    for c in contracts:
        party = c.get("parties", "Unknown")
        entry = by_party.setdefault(party, {"count": 0, "highest_risk": "", "latest_verdict": "", "latest_ts": ""})
        entry["count"] += 1
        if risk_rank.get(c.get("risk_level", ""), 0) >= risk_rank.get(entry["highest_risk"], 0):
            entry["highest_risk"] = c.get("risk_level", "")
        if c.get("timestamp", "") >= entry["latest_ts"]:
            entry["latest_ts"] = c.get("timestamp", "")
            entry["latest_verdict"] = c.get("verdict", "")

    return {
        "risk_counts": risk_counts,
        "top_flags": flag_counter.most_common(10),
        "by_party": by_party,
    }


def render_portfolio_dashboard(contracts: List[Dict[str, Any]]) -> str:
    stats = build_portfolio_stats(contracts)

    cards_html = ""
    for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        n = stats["risk_counts"].get(level, 0)
        cards_html += (
            f'<div class="card"><div class="num" style="color:{RISK_COLOR[level]}">{n}</div>'
            f'<div class="label">{level}</div></div>'
        )

    max_flag_count = max((n for _, n in stats["top_flags"]), default=1)
    flag_rows = ""
    for name, n in stats["top_flags"]:
        pct = int((n / max_flag_count) * 100)
        flag_rows += (
            f"<tr><td>{name}</td><td>{n}</td>"
            f'<td><div class="bar-wrap"><div class="bar" style="width:{pct}%"></div></div></td></tr>'
        )
    if not flag_rows:
        flag_rows = "<tr><td colspan=3>No red flags recorded yet.</td></tr>"

    party_rows = ""
    for party, entry in sorted(stats["by_party"].items(), key=lambda kv: -kv[1]["count"]):
        risk = entry["highest_risk"]
        verdict = entry["latest_verdict"]
        party_rows += (
            f"<tr><td>{party}</td><td>{entry['count']}</td>"
            f'<td><span class="badge" style="background:{RISK_COLOR.get(risk, "#666")}">{risk}</span></td>'
            f'<td><span class="badge" style="background:{VERDICT_COLOR.get(verdict, "#666")}">{verdict}</span></td></tr>'
        )
    if not party_rows:
        party_rows = "<tr><td colspan=4>No contracts analyzed yet.</td></tr>"

    return TEMPLATE.format(
        generated_at=time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        count=len(contracts),
        cards=cards_html,
        flag_rows=flag_rows,
        party_rows=party_rows,
    )


def write_portfolio_dashboard(contracts: List[Dict[str, Any]], out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.write_text(render_portfolio_dashboard(contracts), encoding="utf-8")
    return out_path
