"""
Extracts key time-bound obligations from contract text: renewal dates,
notice periods, and contract terms. Free, offline, regex-based - no LLM
call needed. Feeds `hermes-legal deadlines`, which helps a firm or
freelancer track what's coming up across every contract they've ever
analyzed instead of re-reading each one.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

MONTH_NAMES = (
    r"January|February|March|April|May|June|July|August|September|October|November|December"
)

DATE_PATTERNS = [
    re.compile(rf"({MONTH_NAMES})\s+(\d{{1,2}}),?\s+(\d{{4}})", re.IGNORECASE),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"),
]

TERM_PATTERN = re.compile(r"(?:term of|for a period of|for)\s+(\d+)\s*[-\s]?\s*(day|week|month|year)s?", re.IGNORECASE)
RENEWAL_PATTERN = re.compile(r"auto-?renew\w*.{0,80}?(\d+)\s*[-\s]?\s*(day|week|month|year)s?", re.IGNORECASE)
NOTICE_PATTERN = re.compile(r"(\d+)\s*[-\s]?\s*(day|week|month)s?\s+(?:written\s+|prior\s+)?notice", re.IGNORECASE)

_MONTH_INDEX = {name.lower(): i + 1 for i, name in enumerate([
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
])}


def _parse_date(match: re.Match) -> Optional[datetime]:
    groups = match.groups()
    try:
        if groups[0].isalpha():
            month = _MONTH_INDEX.get(groups[0].lower())
            day, year = int(groups[1]), int(groups[2])
            return datetime(year, month, day)
        if len(groups[0]) == 4:
            return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
        # US-style M/D/Y
        return datetime(int(groups[2]), int(groups[0]), int(groups[1]))
    except (ValueError, TypeError):
        return None


def extract_dates(text: str) -> List[str]:
    found = []
    for pattern in DATE_PATTERNS:
        for m in pattern.finditer(text):
            dt = _parse_date(m)
            if dt:
                found.append(dt.strftime("%Y-%m-%d"))
    return sorted(set(found))


def _duration_to_days(amount: int, unit: str) -> int:
    unit = unit.lower()
    return {"day": 1, "week": 7, "month": 30, "year": 365}.get(unit, 1) * amount


def extract_obligations(text: str) -> List[Dict[str, Any]]:
    """
    Return a list of {kind, description, days} for term length, renewal
    windows, and notice periods found in the text. `days` is an
    approximate duration used for sorting by urgency; it is not a
    calendar deadline unless an explicit date was also found.
    """
    obligations = []

    m = TERM_PATTERN.search(text)
    if m:
        amount, unit = int(m.group(1)), m.group(2)
        obligations.append({
            "kind": "Contract Term",
            "description": f"{amount} {unit}(s)",
            "days": _duration_to_days(amount, unit),
        })

    m = RENEWAL_PATTERN.search(text)
    if m:
        amount, unit = int(m.group(1)), m.group(2)
        obligations.append({
            "kind": "Auto-Renewal Cancellation Window",
            "description": f"{amount} {unit}(s) before renewal",
            "days": _duration_to_days(amount, unit),
        })

    m = NOTICE_PATTERN.search(text)
    if m:
        amount, unit = int(m.group(1)), m.group(2)
        obligations.append({
            "kind": "Termination Notice Period",
            "description": f"{amount} {unit}(s) written notice",
            "days": _duration_to_days(amount, unit),
        })

    explicit_dates = extract_dates(text)
    for d in explicit_dates:
        obligations.append({"kind": "Explicit Date Mentioned", "description": d, "days": None})

    return obligations
