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
    "Indemnification": (
        "This says who has to cover the other side's costs if a third party sues. "
        "Wording like 'any and all claims' can make one party pay for problems it did not cause, "
        "so look for whether it works both ways and whether it has a ceiling."
    ),
    "Amendment": (
        "This decides how the contract can be changed later. If one party can change the terms "
        "on its own, the deal you signed today may not be the deal you have next year."
    ),
    "Assignment": (
        "This decides whether the other side can hand the contract to someone else. Without a "
        "consent requirement, you could end up working with a company you never chose."
    ),
    "Exclusivity": (
        "This can stop you from working with anyone else in a field. It is fair only when it is "
        "limited in scope and time and you are guaranteed something in return, such as minimum fees."
    ),
    "Non-Solicitation": (
        "This stops you from hiring the other side's people or approaching its customers for a "
        "period after the contract ends. Twelve months is common; much longer limits your options."
    ),
    "Penalties": (
        "This sets automatic charges for being late. Daily or weekly percentages add up fast, so "
        "check for a grace period and a maximum total."
    ),
    "Warranty": (
        "This says what promises are made about the quality of the work. 'As is' or a full "
        "disclaimer means you may have no right to a fix if it does not work."
    ),
    "Force Majeure": (
        "This covers events nobody controls, like disasters or war. It matters most when it "
        "allows you to walk away if the event drags on."
    ),
    "Data Protection": (
        "This governs what happens to personal data. Sharing it with third parties without clear "
        "limits can create legal exposure for you under privacy laws."
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
