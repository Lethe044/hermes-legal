"""
Offline extraction of party names and key commercial terms.

Everything here is plain pattern matching: free, instant, and private. It
is used to fill in details the offline scanner would otherwise leave
blank, and to enrich results from any provider that did not return them.
That matters beyond cosmetics: trend detection and the portfolio dashboard
group contracts by party, so contracts that all say "Unknown" can never be
compared with each other.

Extraction is best effort. When nothing reliable is found it returns
nothing rather than guessing.
"""

from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

from .deadlines import DATE_PATTERNS, _parse_date, extract_obligations

# language marker -> (regex for the region after the marker, separator regex between the two parties)
_QUOTED_ROLE = re.compile(r'["\u201c\u201d\u2018\']([^"\u201c\u201d\u2018\']{2,30})["\u201c\u201d\u2019\']')
_MAX_NAME = 60


_SENTENCE_BREAK = re.compile(r"\.\s+(?=[A-Z\u00c0-\u00dd])")
_TRAILING_CAPS = re.compile(r"((?:[A-Z\u00c0-\u00dd][\w.&'-]*\s*){1,5})\s*$")
# Region after the marker word: ends at the closing paren of the second defined role,
# a blank line, or a length cap. Ending at the first ". " would cut "Acme Inc. (" in half.
_REGION = r"(.{3,400}?)(?:\)\s*[.;]|\n\s*\n|$)"


def _cut_sentence(text: str) -> str:
    for m in _SENTENCE_BREAK.finditer(text):
        word = re.search(r"([A-Za-z]+)$", text[: m.start()])
        # Short tokens before a period are almost always abbreviations (Inc., Ltd., Co.)
        if word and len(word.group(1)) >= 5:
            return text[: m.start()]
    return text


def _clean_name(raw: str) -> str:
    name = raw.split("(")[0].split("\n")[0]
    name = _cut_sentence(name)
    name = re.split(r"[;,]", name)[0]
    name = re.sub(r"^\s*(?:the|this|a|an)\s+", "", name, flags=re.IGNORECASE)
    return name.strip(" \t\r\n,;:-")


def _side_to_name(side: str, trailing_caps: bool = False) -> Optional[str]:
    role_match = _QUOTED_ROLE.search(side)
    role = role_match.group(1).strip() if role_match else None
    before_role = side.split("(")[0]
    if trailing_caps:
        # e.g. Turkish "Isbu sozlesme Acme A.S." - keep only the trailing run of capitalized words
        caps = _TRAILING_CAPS.search(before_role.strip())
        before_role = caps.group(1) if caps else before_role
    name = _clean_name(before_role)
    # A lowercase-first "name" is a description ("the individual identified below"),
    # so the defined role ("Contractor") is a better label.
    if (not name or name[0].islower()) and role:
        return role
    if not name:
        return role
    return name[:_MAX_NAME]


def extract_parties(text: str) -> Optional[str]:
    """Return 'A and B' for the contracting parties, or None if not found."""
    head = text[:2000]

    candidates: list = []  # (parts, trailing_caps)

    m = re.search(r"\bbetween\b" + _REGION, head, re.IGNORECASE | re.DOTALL)
    if m:
        seg = m.group(1)
        parts = re.split(r"\)\s*,?\s*and\s+", seg, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) < 2:
            parts = re.split(r"\s+and\s+", seg, maxsplit=1, flags=re.IGNORECASE)
        candidates.append((parts, False))

    m = re.search(r"\bentre\b" + _REGION, head, re.IGNORECASE | re.DOTALL)
    if m:
        candidates.append((re.split(r"\)\s*,?\s*y\s+|\s+y\s+", m.group(1), maxsplit=1, flags=re.IGNORECASE), False))

    m = re.search(r"\bzwischen\b" + _REGION, head, re.IGNORECASE | re.DOTALL)
    if m:
        candidates.append((re.split(r"\)\s*,?\s*und\s+|\s+und\s+", m.group(1), maxsplit=1, flags=re.IGNORECASE), False))

    m = re.search(r"(.{3,300}?\))\s+ile\s+(.{3,300}?)\s+aras[\u0131i]nda", head, re.IGNORECASE | re.DOTALL)
    if m:
        candidates.append(([m.group(1), m.group(2)], True))

    for parts, trailing in candidates:
        if len(parts) < 2:
            continue
        a = _side_to_name(parts[0], trailing_caps=trailing)
        b = _side_to_name(parts[1])
        if a and b:
            return f"{a} and {b}"
    return None


_CURRENCY = (
    r"(?:US\$|\$|€|£|₺)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:per|/|a)\s?(?:hour|hr|day|week|month|year|annum))?"
    r"|\b\d[\d,]*(?:\.\d+)?\s?(?:USD|EUR|GBP|TRY|TL)\b(?:\s?(?:per|/|a)\s?(?:hour|hr|day|week|month|year))?"
)
_AMOUNT = re.compile(_CURRENCY, re.IGNORECASE)
_PAY_WITHIN = re.compile(r"(?:within|in)\s+(\d{1,3})\s+days?\s+of\s+(?:receipt|invoice|the invoice|delivery)", re.IGNORECASE)
_NET = re.compile(r"\bnet\s*-?\s*(\d{1,3})\b", re.IGNORECASE)
_LAW_OF = re.compile(
    r"(?:governed by|construed in accordance with|subject to)\s+(?:and construed in accordance with\s+)?"
    r"the\s+laws?\s+of\s+(?:the\s+)?(?:State of\s+)?([A-Z][A-Za-z ,]{1,45}?)(?:[.;\n]|\s+without|\s+and\s+(?:the\s+)?courts)",
)
_LAW_ADJ = re.compile(r"governed by\s+([A-Z][A-Za-z]{2,30}(?:\s[A-Z][A-Za-z]{2,30})?)\s+law\b")


def _first_date(text: str) -> Optional[Tuple[int, str]]:
    best: Optional[Tuple[int, str]] = None
    for pattern in DATE_PATTERNS:
        for m in pattern.finditer(text):
            dt = _parse_date(m)
            if dt and (best is None or m.start() < best[0]):
                best = (m.start(), dt.strftime("%Y-%m-%d"))
    return best


def extract_key_terms(text: str) -> Dict[str, str]:
    terms: Dict[str, str] = {}

    first = _first_date(text)
    if first:
        terms["Effective date"] = first[1]

    obligations = {o["kind"]: o["description"] for o in extract_obligations(text)}
    if "Contract Term" in obligations:
        terms["Term"] = obligations["Contract Term"]
    if "Termination Notice Period" in obligations:
        terms["Termination notice"] = obligations["Termination Notice Period"]
    if "Auto-Renewal Cancellation Window" in obligations:
        terms["Renewal cancellation window"] = obligations["Auto-Renewal Cancellation Window"]

    amounts = []
    for m in _AMOUNT.finditer(text):
        value = re.sub(r"\s+", " ", m.group(0)).strip()
        if value not in amounts:
            amounts.append(value)
        if len(amounts) == 3:
            break
    if amounts:
        terms["Amounts"] = "; ".join(amounts)

    pay = _PAY_WITHIN.search(text)
    net = _NET.search(text)
    if pay:
        terms["Payment due"] = f"within {pay.group(1)} days"
    elif net:
        terms["Payment due"] = f"Net {net.group(1)}"

    law = _LAW_OF.search(text)
    if law:
        terms["Governing law"] = law.group(1).strip(" ,")
    else:
        adj = _LAW_ADJ.search(text)
        if adj:
            terms["Governing law"] = adj.group(1)

    return terms
