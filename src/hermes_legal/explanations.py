"""
Plain-English explanations of common contract clause categories.

This is deliberately not AI-generated per request - it's a small, free,
offline reference table so `--explain` works even with the offline
provider and never costs an API call. When an LLM provider is active,
these are shown alongside the model's own finding for extra grounding.
"""

from __future__ import annotations

from typing import Dict, List

CLAUSE_EXPLANATIONS: Dict[str, str] = {
    "Termination": (
        "This is the 'how do we end this' clause. It sets how much warning "
        "either side has to give before walking away. A short notice period "
        "means the other side can cut you off (or you can be cut off) with "
        "very little runway to adjust."
    ),
    "Liability": (
        "This decides who pays if something goes wrong and how much. An "
        "'uncapped' or 'unlimited' liability clause means there's no ceiling "
        "on what you could owe - even a small mistake could theoretically "
        "cost far more than the deal is worth."
    ),
    "Intellectual Property": (
        "This decides who owns what gets created. Broad language (like "
        "covering 'any work' or work done on 'personal time') can mean you "
        "sign away rights to things you make outside the actual project."
    ),
    "Non-Compete": (
        "This restricts where you can work or who you can work with after "
        "the relationship ends. The two things that matter most are how "
        "long it lasts and how big an area (industry or geography) it covers."
    ),
    "Auto-Renewal": (
        "This means the contract renews itself automatically unless someone "
        "actively cancels it in time. If the cancellation window is short "
        "and easy to miss, you can end up locked in for another term "
        "without meaning to."
    ),
    "Confidentiality": (
        "This is about keeping shared information secret. 'Perpetual' or "
        "'indefinite' confidentiality means the obligation never expires - "
        "most standard agreements bound it to a few years instead."
    ),
    "Payment Terms": (
        "This sets how and when you get paid (or have to pay). 'Net 30' "
        "means payment is due 30 days after invoicing; longer windows (Net "
        "60, Net 90) mean you wait longer for your money."
    ),
    "Dispute Resolution": (
        "This decides what happens if the two sides disagree - court, "
        "arbitration, or mediation - and who pays for it. Forcing one side "
        "to cover all dispute costs regardless of outcome discourages that "
        "side from ever raising a legitimate complaint."
    ),
    "Governing Law": (
        "This picks which region's laws apply and, often, where any dispute "
        "would have to be handled. A jurisdiction far from you can mean "
        "expensive travel or unfamiliar legal procedure if something goes "
        "wrong."
    ),
}

DEFAULT_EXPLANATION = (
    "No plain-English explanation is available yet for this clause "
    "category - the finding above is still accurate, just without the "
    "extra context."
)


def explain_clause(name: str) -> str:
    return CLAUSE_EXPLANATIONS.get(name, DEFAULT_EXPLANATION)


def attach_explanations(clauses: List[Dict]) -> List[Dict]:
    """Return a new list of clause dicts with a 'plain_explanation' key added."""
    out = []
    for c in clauses:
        c2 = dict(c)
        c2["plain_explanation"] = explain_clause(c.get("name", ""))
        out.append(c2)
    return out
