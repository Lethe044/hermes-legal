"""
Offline provider - a deterministic, rule-based analyzer that needs no API
key, no internet connection, and no third-party account whatsoever.

It is deliberately less nuanced than an LLM-backed provider, but it means
Hermes Legal Advisor is 100% usable for free, forever, with zero signup -
and it works as an instant first pass before a paid or free-tier model
gets a second, deeper look.

The pattern library below is informed by the publicly documented CUAD
(Contract Understanding Atticus Dataset) risk categories, reimplemented
here as lightweight keyword/regex heuristics rather than a trained model.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .base import AnalysisResult, BaseProvider
from ..playbook import Playbook

TURKISH_INDICATORS = [
    "madde", "sözleşme", "taraf", "işbu", "yüklenici",
    "hizmet", "ücret", "fesih", "gizlilik", "rekabet",
]
SPANISH_INDICATORS = [
    "contrato", "cláusula", "las partes", "el presente", "contratista",
    "servicio", "pago", "terminación", "confidencialidad", "competencia",
]
GERMAN_INDICATORS = [
    "vertrag", "klausel", "vertragspartei", "auftragnehmer", "dienstleistung",
    "zahlung", "kündigung", "vertraulichkeit", "wettbewerbsverbot", "haftung",
]

# Each rule: (clause name, patterns that indicate presence, red-flag test, score if
# triggered, human-readable finding, generic negotiation suggestion)
RULES: List[Dict[str, Any]] = [
    {
        "name": "Termination",
        "presence": [r"terminat", r"fesih", r"terminaci[oó]n", r"k[üu]ndigung"],
        "red_flag": re.compile(
            r"(\d+)\s*-?\s*days?\s+(?:written\s+|prior\s+)?notice"
            r"|(\d+)\s*-?\s*g[üu]n[lü]?[üu]?k?\s+(?:yazılı\s+)?bildirim"
            r"|(\d+)\s*-?\s*d[ií]as?\s+de\s+(?:previo\s+)?aviso"
            r"|(\d+)\s*-?\s*tage[n]?\s+(?:vorheriger\s+)?(?:schriftlicher\s+)?k[üu]ndigungsfrist",
            re.IGNORECASE,
        ),
        "threshold_days": 7,
        "score_if_flag": 9,
        "score_if_present": 3,
        "finding": "Termination notice period appears shorter than the 7-day baseline this tool checks for.",
        "suggestion": "Request a minimum 30-day written notice period for termination without cause, "
        "applied equally to both parties.",
    },
    {
        "name": "Liability",
        "presence": [r"liabilit", r"sorumluluk", r"responsabilidad", r"haftung"],
        "red_flag": re.compile(
            r"uncapped|unlimited liability|sınırsız sorumluluk"
            r"|responsabilidad\s+ilimitada|sin\s+l[ií]mite\s+de\s+responsabilidad"
            r"|unbeschr[äa]nkte\s+haftung|unbegrenzte\s+haftung",
            re.IGNORECASE,
        ),
        "score_if_flag": 9,
        "score_if_present": 3,
        "finding": "Liability appears uncapped for at least one party.",
        "suggestion": "Cap total liability at a fixed multiple of fees paid (e.g. 12 months of fees), "
        "applied symmetrically to both parties, with standard carve-outs for gross negligence, "
        "IP infringement, and confidentiality breaches.",
    },
    {
        "name": "Intellectual Property",
        "presence": [r"intellectual property", r"\bIP\b", r"fikri mülkiyet",
                     r"propiedad\s+intelectual", r"geistiges\s+eigentum"],
        "red_flag": re.compile(
            r"all work product|any work.{0,20}(created|developed)|personal time|kişisel zaman"
            r"|todo\s+el\s+trabajo|tiempo\s+personal"
            r"|s[äa]mtliche\s+arbeitsergebnisse|pers[öo]nlicher\s+zeit",
            re.IGNORECASE,
        ),
        "score_if_flag": 8,
        "score_if_present": 3,
        "finding": "IP assignment language may extend beyond work performed under this agreement.",
        "suggestion": "Limit IP assignment strictly to deliverables created within the scope of this "
        "agreement and during engaged working hours.",
    },
    {
        "name": "Non-Compete",
        "presence": [r"non-compete", r"rekabet\s+yasağı", r"no\s+competencia",
                     r"cl[aá]usula\s+de\s+no\s+competencia", r"wettbewerbsverbot"],
        "red_flag": re.compile(
            r"(worldwide|global)\s+non-compete|non-compete.{0,40}(worldwide|global)"
            r"|\b([3-9]|\d{2,})\s*-?\s*year\s+non-compete"
            r"|no\s+competencia\s+(mundial|global)|([3-9]|\d{2,})\s*-?\s*a[ñn]os?\s+de\s+no\s+competencia"
            r"|weltweite[s]?\s+wettbewerbsverbot|([3-9]|\d{2,})\s*-?\s*jahre[s]?\s+wettbewerbsverbot",
            re.IGNORECASE,
        ),
        "score_if_flag": 9,
        "score_if_present": 4,
        "finding": "Non-compete scope or duration looks broader than common market practice (over 1-2 years, "
        "or unrestricted geography).",
        "suggestion": "Narrow the non-compete to a specific, named list of direct competitors, a maximum "
        "of 12 months, and a defined geographic market you actually operate in.",
    },
    {
        "name": "Auto-Renewal",
        "presence": [r"auto-?renew", r"otomatik yenile", r"renovaci[oó]n\s+autom[aá]tica",
                     r"automatische\s+verl[äa]ngerung"],
        "red_flag": re.compile(
            r"(\d{1,2})\s*-?\s*day.{0,20}cancel"
            r"|(\d{1,2})\s*-?\s*d[ií]as?.{0,20}cancelar"
            r"|(\d{1,2})\s*-?\s*tage[n]?.{0,20}k[üu]ndigen",
            re.IGNORECASE,
        ),
        "threshold_days": 30,
        "score_if_flag": 7,
        "score_if_present": 3,
        "finding": "Auto-renewal cancellation window may be shorter than 30 days.",
        "suggestion": "Extend the cancellation/opt-out window to at least 30 days before renewal, with "
        "a reminder notice obligation on the counter-party.",
    },
    {
        "name": "Confidentiality",
        "presence": [r"confidential", r"gizlilik", r"confidencialidad", r"vertraulichkeit"],
        "red_flag": re.compile(
            r"perpetual|indefinite|süresiz|perpetu[ao]|indefinid[ao]|unbefristet|dauerhaft",
            re.IGNORECASE,
        ),
        "score_if_flag": 6,
        "score_if_present": 2,
        "finding": "Confidentiality obligations may be perpetual/indefinite rather than time-bound.",
        "suggestion": "Bound confidentiality obligations to a defined term (commonly 3-5 years after "
        "termination), except for trade secrets which may remain protected as long as they qualify.",
    },
    {
        "name": "Payment Terms",
        "presence": [r"payment", r"ödeme", r"invoice", r"fatura", r"pago", r"factura", r"zahlung", r"rechnung"],
        "red_flag": re.compile(r"net\s*(6[0-9]|[7-9]\d|\d{3,})", re.IGNORECASE),
        "score_if_flag": 6,
        "score_if_present": 2,
        "finding": "Payment terms may extend beyond typical Net-30/Net-45 windows.",
        "suggestion": "Negotiate Net-30 payment terms with a defined late-payment interest rate.",
    },
    {
        "name": "Dispute Resolution",
        "presence": [r"arbitration", r"dispute resolution", r"tahkim", r"uyuşmazlık",
                     r"arbitraje", r"resoluci[oó]n\s+de\s+disputas", r"schiedsverfahren", r"streitbeilegung"],
        "red_flag": re.compile(
            r"(costs?|fees?)\s+(shall\s+be\s+)?(borne|paid)\s+(solely\s+)?by\s+(the\s+)?(contractor|employee|tenant|licensee)"
            r"|(costos?|honorarios?)\s+ser[aá]n\s+(asumidos|pagados)\s+(exclusivamente\s+)?por"
            r"|kosten\s+(werden\s+)?(allein|ausschließlich)\s+von",
            re.IGNORECASE,
        ),
        "score_if_flag": 7,
        "score_if_present": 2,
        "finding": "Arbitration/dispute costs may fall entirely on one party.",
        "suggestion": "Split arbitration costs evenly, or make the losing party responsible for "
        "reasonable fees, rather than assigning them to one named party regardless of outcome.",
    },
    {
        "name": "Governing Law",
        "presence": [r"governing law", r"uygulanacak hukuk", r"ley\s+aplicable", r"anwendbares\s+recht"],
        "red_flag": None,
        "score_if_flag": 0,
        "score_if_present": 2,
        "finding": "Governing law clause present; verify the jurisdiction is convenient for you.",
        "suggestion": "",
    },
]

STANDARD_CLAUSES_BY_TYPE = {
    "Freelance Service Agreement": [
        "payment terms", "intellectual property", "confidentiality",
        "termination", "dispute resolution", "governing law", "liability",
    ],
    "Employment Agreement": [
        "compensation", "intellectual property", "confidentiality",
        "termination", "dispute resolution", "governing law",
    ],
    "NDA": [
        "definition of confidential information", "obligations", "exclusions",
        "term", "remedies", "governing law",
    ],
    "Service Agreement": [
        "scope of services", "payment", "termination", "liability",
        "confidentiality", "governing law",
    ],
}


def detect_language(text: str) -> str:
    lower = text.lower()
    scores = {
        "TR": sum(1 for w in TURKISH_INDICATORS if w in lower),
        "ES": sum(1 for w in SPANISH_INDICATORS if w in lower),
        "DE": sum(1 for w in GERMAN_INDICATORS if w in lower),
    }
    best_lang, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_lang if best_score >= 3 else "EN"


def guess_contract_type(text: str) -> str:
    lower = text.lower()
    if ("non-disclosure" in lower or "nda" in lower or "gizlilik sözleşmesi" in lower
            or "acuerdo de confidencialidad" in lower or "geheimhaltungsvereinbarung" in lower):
        return "NDA"
    if ("employment" in lower or "iş sözleşmesi" in lower or "employee" in lower
            or "contrato de trabajo" in lower or "arbeitsvertrag" in lower):
        return "Employment Agreement"
    if ("freelance" in lower or "independent contractor" in lower or "serbest" in lower
            or "autónomo" in lower or "freiberuflich" in lower):
        return "Freelance Service Agreement"
    return "Service Agreement"


class OfflineProvider(BaseProvider):
    name = "offline"

    def __init__(self, playbook: Optional[Playbook] = None):
        self.playbook = playbook or Playbook()

    def is_available(self) -> bool:
        return True  # always available, no dependencies

    def _effective_rules(self) -> List[Dict[str, Any]]:
        """Merge built-in RULES with playbook overrides and custom rules."""
        overrides = self.playbook.rule_overrides
        merged = []
        for rule in RULES:
            r = dict(rule)
            override = overrides.get(rule["name"])
            if override:
                if "score_if_flag" in override:
                    r["score_if_flag"] = override["score_if_flag"]
                if "score_if_present" in override:
                    r["score_if_present"] = override["score_if_present"]
                if "suggestion" in override:
                    r["suggestion"] = override["suggestion"]
                if "finding" in override:
                    r["finding"] = override["finding"]
            merged.append(r)

        for custom in self.playbook.custom_rules:
            pattern = custom.get("red_flag_pattern")
            merged.append(
                {
                    "name": custom.get("name", "Custom Rule"),
                    "presence": custom.get("presence", []),
                    "red_flag": re.compile(pattern, re.IGNORECASE) if pattern else None,
                    "score_if_flag": custom.get("score_if_flag", 6),
                    "score_if_present": custom.get("score_if_present", 2),
                    "finding": custom.get("finding", ""),
                    "suggestion": custom.get("suggestion", ""),
                }
            )
        return merged

    def analyze(
        self,
        contract_text: str,
        perspective: str = "neutral",
        language_hint: Optional[str] = None,
        memory_context: str = "",
    ) -> AnalysisResult:
        language = language_hint or detect_language(contract_text)
        contract_type = guess_contract_type(contract_text)
        lower = contract_text.lower()

        clauses: List[Dict[str, Any]] = []
        present_names: List[str] = []

        for rule in self._effective_rules():
            present = any(re.search(p, contract_text, re.IGNORECASE) for p in rule["presence"])
            if not present:
                continue
            present_names.append(rule["name"].lower())

            is_flag = False
            if rule["red_flag"] is not None:
                match = rule["red_flag"].search(contract_text)
                if match:
                    if "threshold_days" in rule:
                        try:
                            days = int(next(g for g in match.groups() if g and g.isdigit()))
                            is_flag = days < rule["threshold_days"]
                        except (StopIteration, ValueError):
                            is_flag = True
                    else:
                        is_flag = True

            score = rule["score_if_flag"] if is_flag else rule["score_if_present"]
            clauses.append(
                {
                    "name": rule["name"],
                    "score": score,
                    "is_red_flag": is_flag,
                    "finding": rule["finding"] if is_flag else f"{rule['name']} clause present; no obvious red flag detected by pattern scan.",
                    "negotiation_suggestion": rule["suggestion"] if is_flag else "",
                }
            )

        expected = STANDARD_CLAUSES_BY_TYPE.get(contract_type, [])
        missing = [c for c in expected if not any(c in p for p in present_names)]

        if clauses:
            avg = sum(c["score"] for c in clauses) / len(clauses)
        else:
            avg = 5.0
        t = self.playbook.thresholds
        if avg >= t["high"]:
            overall_risk = "CRITICAL" if avg >= t["critical"] else "HIGH"
        elif avg >= t["medium"]:
            overall_risk = "MEDIUM"
        else:
            overall_risk = "LOW"

        red_flags = [c for c in clauses if c["is_red_flag"]]
        if len(red_flags) >= 3 or overall_risk == "CRITICAL":
            verdict = "REJECT"
        elif red_flags or overall_risk in ("HIGH", "MEDIUM"):
            verdict = "NEGOTIATE"
        else:
            verdict = "SIGN"

        summary = (
            f"Offline pattern scan found {len(clauses)} recognizable clause categories, "
            f"{len(red_flags)} of which trip a known red-flag pattern. "
            f"This is a fast heuristic pass, not a substitute for a full LLM or attorney review."
        )
        recommendations = [c["negotiation_suggestion"] for c in red_flags if c["negotiation_suggestion"]]
        if missing:
            recommendations.append(
                "Add the missing standard clauses listed above before signing."
            )
        if not recommendations:
            recommendations.append("No major red flags detected by the offline scan; a full review is still advised.")

        return AnalysisResult(
            contract_type=contract_type,
            parties="Unknown (offline mode does not extract named parties)",
            language=language,
            clauses=clauses,
            missing_clauses=missing,
            key_terms={},
            overall_risk=overall_risk,
            verdict=verdict,
            summary=summary,
            recommendations=recommendations,
            provider=self.name,
        )
