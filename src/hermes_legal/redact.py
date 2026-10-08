"""
Privacy mode.

Contracts often contain names, contact details, and account numbers that
should never leave the machine. `redact_text` masks the most common kinds
of sensitive details with stable placeholders so the structure and the
legal terms of the contract stay intact for analysis.

This is a best-effort, pattern-based safety net, not a guarantee. It
catches well-formatted emails, phone numbers, IBANs, card-like numbers,
and tax/ID-like numbers, plus any names the caller lists explicitly. For
truly privileged material, use the offline provider or a local Ollama
model, which never send text anywhere.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, Iterable, List, Optional, Tuple

def _digits(value: str) -> int:
    return sum(ch.isdigit() for ch in value)


def _looks_like_phone(value: str) -> bool:
    # 9 to 15 digits covers national and international numbers while leaving
    # dates (8 digits), short reference numbers, and ordinary amounts alone.
    return 9 <= _digits(value) <= 15


# (kind, pattern, optional validator that must return True for a match to be masked)
PATTERNS: List[Tuple[str, re.Pattern, Optional[Callable[[str], bool]]]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), None),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){3,7}(?:[ ]?[A-Z0-9]{1,4})?\b"), None),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b"), lambda v: 13 <= _digits(v) <= 19),
    ("ID", re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{11}\b"), None),
    ("PHONE", re.compile(r"(?<![\w.])\+?\(?\d[\d ()\-.]{7,17}\d(?![\w])"), _looks_like_phone),
]


def redact_text(text: str, names: Iterable[str] = ()) -> Tuple[str, Dict[str, str]]:
    """
    Return (redacted_text, mapping). The mapping goes from placeholder to the
    original value so the caller can show it locally if wanted. Each distinct
    value always gets the same placeholder.
    """
    mapping: Dict[str, str] = {}
    reverse: Dict[str, str] = {}
    counters: Dict[str, int] = {}

    def placeholder(kind: str, value: str) -> str:
        if value in reverse:
            return reverse[value]
        counters[kind] = counters.get(kind, 0) + 1
        tag = f"[{kind}_{counters[kind]}]"
        reverse[value] = tag
        mapping[tag] = value
        return tag

    redacted = text

    for i, name in enumerate(sorted({n for n in names if n and n.strip()}, key=len, reverse=True)):
        pattern = re.compile(re.escape(name.strip()), re.IGNORECASE)
        redacted = pattern.sub(lambda m, n=name: placeholder("PARTY", n.strip().lower()), redacted)

    for kind, pattern, validator in PATTERNS:
        def _sub(m, k=kind, v=validator):
            value = m.group(0)
            if v is not None and not v(value):
                return value
            return placeholder(k, value)

        redacted = pattern.sub(_sub, redacted)

    return redacted, mapping


def is_remote_provider(provider_name: str) -> bool:
    """Providers that send contract text over the network."""
    return provider_name in {"groq", "gemini", "openrouter"}
