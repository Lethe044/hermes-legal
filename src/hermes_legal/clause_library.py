"""
Model replacement clauses.

Redline suggestions are far more useful when they come with actual
drafted language instead of only advice. This is a small, free, offline
library of balanced starting-point clauses for the categories the rule
engine checks. They are neutral templates meant to be adapted, not legal
advice. Placeholders in [BRACKETS] must be filled in before use.
"""

from __future__ import annotations

from typing import Dict, Optional

MODEL_CLAUSES: Dict[str, str] = {
    "Termination": (
        "Either party may terminate this Agreement without cause by giving the other party "
        "not less than thirty (30) days' prior written notice. Either party may terminate "
        "immediately by written notice if the other party materially breaches this Agreement "
        "and fails to cure the breach within fifteen (15) days of receiving written notice "
        "of it. Upon termination, the Client shall pay for all work performed up to the "
        "effective date of termination."
    ),
    "Liability": (
        "Each party's total aggregate liability arising out of or related to this Agreement "
        "shall not exceed the total fees paid or payable under this Agreement in the twelve "
        "(12) months preceding the claim. Neither party shall be liable for indirect, "
        "incidental, or consequential damages. This limitation does not apply to liability "
        "for gross negligence, willful misconduct, breach of confidentiality, or infringement "
        "of the other party's intellectual property."
    ),
    "Intellectual Property": (
        "Upon full payment, Contractor assigns to Client all right, title, and interest in the "
        "deliverables created specifically for Client under this Agreement. Contractor retains "
        "ownership of all pre-existing materials, tools, and general know-how, and grants "
        "Client a non-exclusive, perpetual license to use them as embedded in the deliverables. "
        "Nothing in this Agreement assigns any work created outside the scope of this "
        "Agreement or on Contractor's own time and resources."
    ),
    "Non-Compete": (
        "For a period of twelve (12) months following termination, [PARTY] shall not directly "
        "provide the same services to the following named competitors of [OTHER PARTY]: "
        "[LIST OF COMPETITORS], within [DEFINED GEOGRAPHIC MARKET]. This restriction does not "
        "prevent [PARTY] from working in the same industry generally, and applies only to the "
        "extent enforceable under applicable law."
    ),
    "Auto-Renewal": (
        "This Agreement renews automatically for successive terms equal to the initial term "
        "unless either party gives written notice of non-renewal at least thirty (30) days "
        "before the end of the then-current term. The provider shall send a written renewal "
        "reminder no earlier than sixty (60) and no later than forty-five (45) days before "
        "the renewal date."
    ),
    "Confidentiality": (
        "Each party shall keep the other party's Confidential Information confidential and use "
        "it only for the purposes of this Agreement. These obligations continue for three (3) "
        "years after termination of this Agreement, except that obligations regarding trade "
        "secrets continue for as long as the information remains a trade secret under "
        "applicable law."
    ),
    "Payment Terms": (
        "Client shall pay each undisputed invoice within thirty (30) days of receipt. Amounts "
        "not paid when due accrue interest at the lesser of 1.5% per month or the maximum "
        "rate permitted by law. Client shall notify Contractor of any good-faith dispute "
        "within ten (10) days of receiving the invoice and pay the undisputed portion on time."
    ),
    "Dispute Resolution": (
        "The parties shall first attempt to resolve any dispute through good-faith negotiation "
        "for thirty (30) days, then through non-binding mediation. If unresolved, the dispute "
        "shall be finally resolved by [ARBITRATION / COURT] in [VENUE]. The costs of mediation "
        "and any arbitrator shall be shared equally, and each party bears its own legal fees "
        "unless the tribunal decides otherwise."
    ),
    "Governing Law": (
        "This Agreement is governed by the laws of [JURISDICTION], without regard to its "
        "conflict of laws principles. The parties submit to the non-exclusive jurisdiction of "
        "the courts of [JURISDICTION] for any proceeding arising out of this Agreement."
    ),
    "Indemnification": (
        "Each party (the 'Indemnifying Party') shall indemnify the other against third-party claims "
        "to the extent caused by the Indemnifying Party's breach of this Agreement or its negligence "
        "or willful misconduct. The indemnified party shall give prompt written notice of the claim, "
        "allow the Indemnifying Party to control the defense, and cooperate reasonably. The "
        "Indemnifying Party's total liability under this section is subject to the limitation of "
        "liability in this Agreement."
    ),
    "Amendment": (
        "This Agreement may be amended only by a written document signed by both parties. If a "
        "party proposes a change to recurring fees or service terms, it shall give at least thirty "
        "(30) days' written notice, and the other party may terminate this Agreement without "
        "penalty before the change takes effect."
    ),
    "Assignment": (
        "Neither party may assign or transfer this Agreement, in whole or in part, without the "
        "other party's prior written consent, which shall not be unreasonably withheld. Either "
        "party may assign this Agreement to a successor in a merger or sale of all or substantially "
        "all of its business, provided it gives prompt written notice and the successor is not a "
        "direct competitor of the other party."
    ),
    "Exclusivity": (
        "During the term, [PARTY] shall not provide [DEFINED SERVICES] to [DEFINED COMPETITORS] in "
        "[DEFINED FIELD]. This restriction applies only while [OTHER PARTY] pays at least [MINIMUM "
        "FEES] per [PERIOD], and does not limit [PARTY] from providing other services or working "
        "with other customers."
    ),
    "Non-Solicitation": (
        "For twelve (12) months after termination, neither party shall knowingly solicit for "
        "employment any employee of the other party with whom it worked directly during the "
        "engagement. General advertisements not targeted at the other party's employees do not "
        "breach this section."
    ),
    "Penalties": (
        "If [PARTY] fails to deliver by the agreed date for reasons within its control, [OTHER "
        "PARTY] may claim liquidated damages of [PERCENT]% of the affected fees for each full week "
        "of delay after a grace period of [NUMBER] days, up to a maximum of [PERCENT]% of the total "
        "fees. Liquidated damages are the sole remedy for the delay."
    ),
    "Warranty": (
        "Contractor warrants that the deliverables will materially conform to the agreed "
        "specifications for [NUMBER] days after delivery. If they do not, Contractor shall correct "
        "the nonconformity at no additional charge within a reasonable time. Except as stated in "
        "this section, no other warranties are given to the extent permitted by law."
    ),
    "Force Majeure": (
        "Neither party is liable for delay or failure caused by events beyond its reasonable "
        "control, such as natural disaster, war, government action, or widespread utility failure, "
        "provided it notifies the other party promptly and uses reasonable efforts to resume "
        "performance. If the event continues for more than sixty (60) days, either party may "
        "terminate this Agreement by written notice."
    ),
    "Data Protection": (
        "Each party shall process personal data received under this Agreement only to perform this "
        "Agreement and in compliance with applicable data protection law. Neither party shall sell "
        "personal data or share it with a third party except under a written agreement that "
        "imposes equivalent protections. Each party shall notify the other without undue delay "
        "after becoming aware of a personal data breach affecting the other party's data."
    ),
}


def get_model_clause(name: str) -> Optional[str]:
    return MODEL_CLAUSES.get(name)


def attach_model_clauses(clauses: list) -> list:
    """Return new clause dicts with a 'model_language' key for flagged or suggested clauses."""
    out = []
    for c in clauses:
        c2 = dict(c)
        if c.get("is_red_flag") or c.get("negotiation_suggestion"):
            model = get_model_clause(c.get("name", ""))
            if model:
                c2["model_language"] = model
        out.append(c2)
    return out
