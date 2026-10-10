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
from ..extract import extract_key_terms, extract_parties
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

# Perspective handling for the offline engine.
#
# The pattern scan finds risky language but cannot tell which party it
# binds. These adjustments are therefore deliberately conservative: for
# the party that usually holds the pen (hiring side), one-sided terms
# that normally bind the service provider are softened and annotated;
# for the service-providing side, payment and renewal terms matter a bit
# more. Anything else is left exactly as scanned.
HIRING_SIDE = {"client", "employer", "landlord"}
SERVICE_SIDE = {"contractor", "employee", "vendor", "tenant"}
PROVIDER_BOUND_CLAUSES = {"Liability", "Non-Compete", "Intellectual Property", "Dispute Resolution"}
SERVICE_SENSITIVE_CLAUSES = {"Payment Terms", "Auto-Renewal"}


def adjust_for_perspective(name: str, score: int, is_flag: bool, finding: str, perspective: str):
    """Return (score, is_flag, finding) adjusted for the reviewing party."""
    p = (perspective or "neutral").lower()
    if p in HIRING_SIDE and is_flag and name in PROVIDER_BOUND_CLAUSES:
        new_score = max(1, score - 3)
        note = (f" (Reviewing as {p}: this type of term usually binds the other side, "
                f"so it is scored lower. Confirm which party it actually binds.)")
        return new_score, new_score >= 6, finding + note
    if p in SERVICE_SIDE and name in SERVICE_SENSITIVE_CLAUSES and score >= 2:
        new_score = min(10, score + 1)
        return new_score, is_flag, finding
    return score, is_flag, finding


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

_F = re.IGNORECASE

RULES.extend([
    {
        "name": "Indemnification",
        "presence": [r"indemnif", r"hold harmless", r"tazmin", r"indemniz", r"freistell", r"schadlos"],
        "red_flag": re.compile(
            r"(?:shall|agrees? to|will)\s+(?:defend,?\s+)?indemnif\w*[^.]{0,80}\b(?:any and all|all)\b[^.]{0,40}(?:claims?|losses|damages|liabilit)"
            r"|indemnif\w*[^.]{0,60}(?:regardless of|including)[^.]{0,30}(?:negligence|fault)"
            r"|(?:s[ıi]n[ıi]rs[ıi]z|t[üu]m zararlar[ıi])\s+tazmin"
            r"|indemnizar[^.]{0,60}todos?\s+los\s+(?:da[ñn]os|gastos)"
            r"|(?:alle|s[äa]mtliche)\s+sch[äa]den[^.]{0,40}freistell",
            _F,
        ),
        "score_if_flag": 8,
        "score_if_present": 3,
        "finding": "Indemnification language looks broad (any and all claims) or may bind only one party.",
        "suggestion": "Make indemnification mutual, limit it to third-party claims caused by the indemnifying "
        "party's breach or negligence, and subject it to the same liability cap as the rest of the agreement.",
    },
    {
        "name": "Amendment",
        "presence": [r"\bamend(?:ment|ed|s)?\b", r"modif(?:y|ication)", r"de[ğg]i[şs]iklik", r"modificaci[oó]n", r"[äa]nderung"],
        "red_flag": re.compile(
            r"(?:may|can|reserves? the right to|has the right to)\s+(?:unilaterally\s+)?(?:amend|modify|change|update|revise)\s+"
            r"(?:this agreement|these terms|the terms|the agreement|any term)[^.]{0,80}"
            r"(?:at any time|sole discretion|without (?:prior )?(?:notice|consent|approval)|from time to time)"
            r"|tek tarafl[ıi] olarak[^.]{0,40}de[ğg]i[şs]tir"
            r"|modificar\s+unilateralmente"
            r"|einseitig[^.]{0,30}(?:[äa]ndern|anpassen)",
            _F,
        ),
        "score_if_flag": 8,
        "score_if_present": 1,
        "finding": "One party may change the terms on its own, without the other party's agreement.",
        "suggestion": "Require any amendment to be in writing and signed by both parties. If unilateral changes "
        "are unavoidable, require at least 30 days' notice and a right to terminate without penalty.",
    },
    {
        "name": "Assignment",
        "presence": [r"\bassign", r"devir", r"cesi[oó]n", r"abtret"],
        "red_flag": re.compile(
            r"(?<!neither party )(?<!no party )(?:may|can|is entitled to)\s+assign[^.]{0,80}without[^.]{0,30}(?:consent|approval|notice)"
            r"|assign[^.]{0,40}freely"
            r"|(?:haklar[ıi]n[ıi]|s[öo]zle[şs]meyi)[^.]{0,30}devredebilir"
            r"|ceder[^.]{0,40}sin\s+consentimiento"
            r"|ohne\s+zustimmung[^.]{0,30}abtreten",
            _F,
        ),
        "score_if_flag": 6,
        "score_if_present": 1,
        "finding": "A party may transfer the agreement to someone else without the other party's consent.",
        "suggestion": "Require prior written consent for assignment by either party, with a narrow exception "
        "for a merger or sale of the whole business, and a right to terminate if the assignee is a competitor.",
    },
    {
        "name": "Exclusivity",
        "presence": [r"exclusiv", r"m[üu]nhas[ıi]r", r"exclusividad", r"exklusiv"],
        "red_flag": re.compile(
            r"exclusive(?:ly)?\s+(?:to|for|with|basis)"
            r"|shall not\s+(?:provide|perform|offer|render)[^.]{0,60}(?:to|for)\s+(?:any\s+)?(?:other|third)"
            r"|m[üu]nhas[ıi]ran"
            r"|exclusividad\s+(?:total|absoluta)"
            r"|ausschlie[ßs]lich\s+f[üu]r",
            _F,
        ),
        "score_if_flag": 7,
        "score_if_present": 2,
        "finding": "Exclusivity language may stop one party from working with anyone else.",
        "suggestion": "Limit exclusivity to a defined field and a defined period, and make it conditional on "
        "minimum guaranteed fees or volume from the other party.",
    },
    {
        "name": "Non-Solicitation",
        "presence": [r"non-?solicit", r"solicit", r"i[şs][çc]i [çc]ekme", r"personel [çc]ekme", r"captaci[oó]n de", r"abwerb"],
        "red_flag": re.compile(
            r"solicit[^.]{0,80}?(\d{1,2})\s*-?\s*years?|(\d{1,2})\s*-?\s*years?[^.]{0,60}solicit",
            _F,
        ),
        "max_value": 2,
        "score_if_flag": 6,
        "score_if_present": 2,
        "finding": "Non-solicitation restriction lasts longer than the 2 years this tool treats as reasonable.",
        "suggestion": "Limit non-solicitation of employees and customers to 12 months after termination, and only "
        "for people or customers the party actually dealt with during the engagement.",
    },
    {
        "name": "Penalties",
        "presence": [r"liquidated damages", r"penalt", r"cezai [şs]art", r"cl[aá]usula penal", r"vertragsstrafe"],
        "red_flag": re.compile(
            r"%\s*(?:per|a|each)\s*(?:day|week)"
            r"|penalt\w+[^.]{0,60}(?:per day|daily|each day)"
            r"|cezai [şs]art[^.]{0,60}(?:g[üu]nl[üu]k|her g[üu]n)"
            r"|vertragsstrafe[^.]{0,60}(?:pro tag|t[äa]glich)",
            _F,
        ),
        "score_if_flag": 7,
        "score_if_present": 3,
        "finding": "Penalty or liquidated damages accrue at a daily or weekly rate that can add up quickly.",
        "suggestion": "Cap total liquidated damages at a fixed percentage of the contract value, make them the "
        "sole remedy for the delay, and start the clock only after a reasonable grace period.",
    },
    {
        "name": "Warranty",
        "presence": [r"warrant", r"garanti", r"garant[ií]a", r"gew[äa]hrleistung"],
        "red_flag": re.compile(
            r"\bas[- ]is\b|without\s+(?:any\s+)?warrant|disclaims?\s+(?:all|any)\s+(?:implied\s+)?warrant"
            r"|hi[çc]bir\s+garanti|sin\s+garant[ií]a|ohne\s+gew[äa]hrleistung",
            _F,
        ),
        "score_if_flag": 5,
        "score_if_present": 2,
        "finding": "Warranties are disclaimed or the work is provided 'as is'.",
        "suggestion": "Ask for a basic warranty that the work will conform to the agreed specification for a "
        "defined period, with a duty to fix defects at no extra charge.",
    },
    {
        "name": "Force Majeure",
        "presence": [r"force majeure", r"m[üu]cbir sebep", r"fuerza mayor", r"h[öo]here gewalt"],
        "red_flag": None,
        "score_if_flag": 0,
        "score_if_present": 1,
        "finding": "Force majeure clause present; check that it covers events relevant to you and allows termination if it lasts long.",
        "suggestion": "",
    },
    {
        "name": "Data Protection",
        "presence": [r"personal data", r"data protection", r"\bgdpr\b", r"\bkvkk\b", r"ki[şs]isel veri",
                     r"datos personales", r"personenbezogene", r"datenschutz"],
        "red_flag": re.compile(
            r"(?:sell|share|disclose|transfer)[^.]{0,50}personal data[^.]{0,60}(?:third part|affiliates|any purpose)"
            r"|ki[şs]isel veri[^.]{0,60}[üu][çc][üu]nc[üu]",
            _F,
        ),
        "score_if_flag": 8,
        "score_if_present": 2,
        "finding": "Personal data may be shared with third parties or affiliates without clear limits.",
        "suggestion": "Limit use of personal data to performing the agreement, require a data processing "
        "agreement for any third party, and require prompt notice of any breach.",
    },
])
PROVIDER_BOUND_CLAUSES.update({"Indemnification", "Exclusivity", "Penalties", "Non-Solicitation"})

# Each expected clause is (label, patterns). A clause counts as present if ANY pattern appears
# in the text, so a contract that covers a topic in its own words is not reported as missing.
_PAYMENT = r"payment|invoice|\bfees?\b|compensation|[öo]deme|fatura|pago|factura|zahlung|rechnung"
_IP = r"intellectual property|work product|ownership of|fikri|propiedad intelectual|geistiges eigentum"
_CONF = r"confidential|gizlilik|confidencialidad|vertraulich"
_TERMINATION = r"terminat|fesih|terminaci[oó]n|k[üu]ndigung"
_DISPUTE = r"arbitrat|dispute|jurisdiction|\bcourts?\b|uyu[şs]mazl[ıi]k|tahkim|mahkeme|arbitraje|streit|schieds"
_LAW = r"governing law|governed by|laws? of|uygulanacak hukuk|hukuk|ley aplicable|anwendbares recht"
_LIAB = r"liabilit|sorumluluk|responsabilidad|haftung"

EXPECTED_CLAUSES: Dict[str, List[tuple]] = {
    "Freelance Service Agreement": [
        ("payment terms", [_PAYMENT]), ("intellectual property", [_IP]), ("confidentiality", [_CONF]),
        ("termination", [_TERMINATION]), ("dispute resolution", [_DISPUTE]),
        ("governing law", [_LAW]), ("liability", [_LIAB]),
    ],
    "Employment Agreement": [
        ("compensation", [r"salary|compensation|wage|maa[şs]|[üu]cret|salario|gehalt|verg[üu]tung"]),
        ("intellectual property", [_IP]), ("confidentiality", [_CONF]), ("termination", [_TERMINATION]),
        ("dispute resolution", [_DISPUTE]), ("governing law", [_LAW]),
    ],
    "NDA": [
        ("definition of confidential information", [r"confidential information|gizli bilgi|informaci[oó]n confidencial|vertrauliche informationen"]),
        ("obligations", [r"shall (?:not )?(?:disclose|use)|obligations?|in confidence|y[üu]k[üu]ml[üu]l[üu]k|obligaciones|verpflichtungen"]),
        ("exclusions", [r"exclu|does not include|publicly available|public domain|istisna|excepciones|ausnahmen"]),
        ("term", [r"\bterm\b|\byears?\b|survive|s[üu]re|plazo|dauer|laufzeit"]),
        ("remedies", [r"remed|injunct|equitable relief|damages|tazminat|recurso|abhilfe|unterlassung"]),
        ("governing law", [_LAW]),
    ],
    "Service Agreement": [
        ("scope of services", [r"services|scope|statement of work|hizmet|servicios|dienstleistung"]),
        ("payment", [_PAYMENT]), ("termination", [_TERMINATION]), ("liability", [_LIAB]),
        ("confidentiality", [_CONF]), ("governing law", [_LAW]),
    ],
    "Lease Agreement": [
        ("premises", [r"premises|property|leased|kiralanan|inmueble|mietobjekt"]),
        ("rent", [r"\brent\b|kira bedeli|\bkira\b|alquiler|\bmiete\b"]),
        ("term", [r"\bterm\b|\byears?\b|\bmonths?\b|s[üu]re|plazo|laufzeit"]),
        ("security deposit", [r"deposit|depozito|fianza|kaution"]),
        ("maintenance and repairs", [r"maintenance|repair|bak[ıi]m|mantenimiento|instandhaltung"]),
        ("termination", [_TERMINATION]), ("governing law", [_LAW]),
    ],
    "Software / SaaS License": [
        ("license grant", [r"licen[sc]e|grant|lisans|licencia|lizenz"]),
        ("fees", [_PAYMENT]), ("term and termination", [_TERMINATION]),
        ("data protection", [r"personal data|data protection|\bgdpr\b|\bkvkk\b|ki[şs]isel veri|datos personales|datenschutz"]),
        ("limitation of liability", [_LIAB]), ("warranty", [r"warrant|garanti|garant[ií]a|gew[äa]hrleistung"]),
        ("support or service levels", [r"support|service level|\bsla\b|uptime|destek|soporte"]),
        ("governing law", [_LAW]),
    ],
}

# Kept for backwards compatibility with anything that imported the old name.
STANDARD_CLAUSES_BY_TYPE = {k: [label for label, _ in v] for k, v in EXPECTED_CLAUSES.items()}


def detect_language(text: str) -> str:
    lower = text.lower()
    scores = {
        "TR": sum(1 for w in TURKISH_INDICATORS if w in lower),
        "ES": sum(1 for w in SPANISH_INDICATORS if w in lower),
        "DE": sum(1 for w in GERMAN_INDICATORS if w in lower),
    }
    best_lang, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_lang if best_score >= 3 else "EN"


TYPE_KEYWORDS: Dict[str, List[str]] = {
    "NDA": [r"non-?disclosure", r"\bnda\b", r"confidentiality agreement", r"gizlilik s[öo]zle[şs]mesi",
            r"acuerdo de confidencialidad", r"geheimhaltungs"],
    "Employment Agreement": [r"employment (?:agreement|contract)", r"\bemployer\b", r"\bemployee\b",
                             r"i[şs] s[öo]zle[şs]mesi", r"contrato de trabajo", r"arbeitsvertrag"],
    "Freelance Service Agreement": [r"freelanc", r"consult(?:ing|ant)", r"independent contractor", r"\bcontractor\b", r"serbest [çc]al",
                                    r"aut[oó]nomo", r"freiberuf"],
    "Lease Agreement": [r"\blease\b", r"\btenant\b", r"\blandlord\b", r"kira s[öo]zle[şs]mesi",
                        r"arrendamiento", r"mietvertrag"],
    "Software / SaaS License": [r"software as a service", r"\bsaas\b", r"license agreement", r"subscription",
                                r"end[- ]user", r"terms of service", r"lisans s[öo]zle[şs]mesi",
                                r"licencia de software", r"softwarelizenz"],
    "Service Agreement": [r"services? agreement", r"master services", r"hizmet s[öo]zle[şs]mesi",
                          r"contrato de servicios", r"dienstleistungsvertrag"],
}


def _a(noun: str) -> str:
    """'a' or 'an' for the given noun phrase ('an NDA', 'an Employment Agreement', 'a Lease Agreement')."""
    if noun.startswith(("NDA", "SaaS")) or noun[:1].lower() in "aeiou":
        return "an"
    return "a"


def guess_contract_type(text: str) -> str:
    """
    Score every known type by keyword hits. A hit in the title (first 300
    characters) counts heavily; repeated hits in the body count a little,
    capped so one long contract cannot drown out the title. Ties go to the
    more specific type, which is listed first.
    """
    title = text[:300].lower()
    body = text.lower()
    best_type, best_score = "Service Agreement", 0
    for contract_type, patterns in TYPE_KEYWORDS.items():
        score = 0
        for pat in patterns:
            if re.search(pat, title):
                score += 5
            score += min(len(re.findall(pat, body)), 3)
        if score > best_score:
            best_type, best_score = contract_type, score
    return best_type


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
            # A rule whose red-flag pattern matches is present by definition, even if the
            # wording avoided the usual keywords.
            if not present and rule["red_flag"] is not None and rule["red_flag"].search(contract_text):
                present = True
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
                    elif "max_value" in rule:
                        try:
                            value = int(next(g for g in match.groups() if g and g.isdigit()))
                            is_flag = value > rule["max_value"]
                        except (StopIteration, ValueError):
                            is_flag = True
                    else:
                        is_flag = True

            score = rule["score_if_flag"] if is_flag else rule["score_if_present"]
            finding = rule["finding"] if is_flag else f"{rule['name']} clause present; no obvious red flag detected by pattern scan."
            score, is_flag, finding = adjust_for_perspective(rule["name"], score, is_flag, finding, perspective)
            clauses.append(
                {
                    "name": rule["name"],
                    "score": score,
                    "is_red_flag": is_flag,
                    "finding": finding,
                    "negotiation_suggestion": rule["suggestion"] if is_flag else "",
                }
            )

        expected = EXPECTED_CLAUSES.get(contract_type, [])
        missing = [
            label for label, patterns in expected
            if not any(re.search(p, contract_text, re.IGNORECASE) for p in patterns)
        ]

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

        # The average alone can hide a single serious problem among many harmless clauses,
        # so the overall level is never lower than the worst individual clause warrants.
        floor = None
        if any(c["score"] >= 9 for c in clauses):
            floor = "HIGH"
        elif red_flags:
            floor = "MEDIUM"
        order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if floor and order.index(overall_risk) < order.index(floor):
            overall_risk = floor

        if len(red_flags) >= 3 or overall_risk == "CRITICAL":
            verdict = "REJECT"
        elif red_flags or overall_risk in ("HIGH", "MEDIUM"):
            verdict = "NEGOTIATE"
        else:
            verdict = "SIGN"

        parties = extract_parties(contract_text) or "Unknown (names not found in the text)"
        key_terms = extract_key_terms(contract_text)

        if red_flags:
            worst = sorted(red_flags, key=lambda c: -c["score"])[:3]
            flagged_text = ", ".join(f"{c['name']} ({c['score']}/10)" for c in worst)
            summary = (
                f"Offline scan of {_a(contract_type)} {contract_type} found {len(clauses)} recognizable clause categories and "
                f"{len(red_flags)} red flag(s), most serious: {flagged_text}. "
            )
        else:
            summary = (
                f"Offline scan of {_a(contract_type)} {contract_type} found {len(clauses)} recognizable clause categories "
                f"and no known red-flag patterns. "
            )
        if missing:
            summary += f"Not found in the text: {', '.join(missing)}. "
        summary += "This is a fast pattern scan, not a substitute for an LLM or attorney review."
        recommendations = [c["negotiation_suggestion"] for c in red_flags if c["negotiation_suggestion"]]
        if missing:
            recommendations.append(
                "Add the missing standard clauses listed above before signing."
            )
        if not recommendations:
            recommendations.append("No major red flags detected by the offline scan; a full review is still advised.")

        return AnalysisResult(
            contract_type=contract_type,
            parties=parties,
            language=language,
            clauses=clauses,
            missing_clauses=missing,
            key_terms=key_terms,
            overall_risk=overall_risk,
            verdict=verdict,
            summary=summary,
            recommendations=recommendations,
            provider=self.name,
        )
