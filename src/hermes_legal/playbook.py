"""
Playbook system - lets a firm or individual customize risk scoring and
negotiation language without touching any code.

A playbook is a YAML file at ~/.hermes-legal/playbook.yaml (or a path
passed with --playbook). It can:

- override the score or suggestion text of any built-in rule by name
- add brand new custom red-flag rules
- set a firm name that appears on generated reports and PDFs
- set default risk thresholds for the SIGN/NEGOTIATE/REJECT verdict

This is the main lever a law firm would pull to make the tool match their
own house style before handing it to clients or non-technical staff.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

DEFAULT_PLAYBOOK_PATH = Path.home() / ".hermes-legal" / "playbook.yaml"

EXAMPLE_PLAYBOOK = """\
# Hermes Legal Advisor - firm playbook
# Customize risk scoring and negotiation language without touching code.
# Place this file at ~/.hermes-legal/playbook.yaml, or point --playbook at it.

firm_name: "Your Firm Name"

# Override any built-in rule by clause name. Only the fields you set are
# changed; everything else keeps its default.
rule_overrides:
  Non-Compete:
    score_if_flag: 10
    suggestion: "Our firm's standard position: no non-compete longer than 6 months, single named market."
  Liability:
    score_if_flag: 8

# Add entirely new red-flag rules specific to your practice area.
custom_rules:
  - name: "Governing Law - Foreign Jurisdiction"
    presence:
      - "governing law"
    red_flag_pattern: "laws of (England|Singapore|Hong Kong)"
    score_if_flag: 6
    finding: "Governing law is a foreign jurisdiction unfamiliar to most local clients."
    suggestion: "Request governing law and venue in the client's home jurisdiction where possible."

# Verdict thresholds (average clause score -> overall risk label).
# Defaults shown below.
thresholds:
  critical: 8
  high: 7
  medium: 4
"""


class Playbook:
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self.data = data or {}

    @property
    def firm_name(self) -> Optional[str]:
        return self.data.get("firm_name")

    @property
    def rule_overrides(self) -> Dict[str, Dict[str, Any]]:
        return self.data.get("rule_overrides", {}) or {}

    @property
    def custom_rules(self) -> List[Dict[str, Any]]:
        return self.data.get("custom_rules", []) or []

    @property
    def thresholds(self) -> Dict[str, float]:
        defaults = {"critical": 8, "high": 7, "medium": 4}
        defaults.update(self.data.get("thresholds", {}) or {})
        return defaults

    def prompt_addendum(self) -> str:
        """Extra instructions injected into LLM-provider prompts."""
        parts = []
        if self.firm_name:
            parts.append(f"You are reviewing on behalf of {self.firm_name}.")
        for name, override in self.rule_overrides.items():
            if "suggestion" in override:
                parts.append(f"For {name} clauses, prefer this house position: {override['suggestion']}")
        for rule in self.custom_rules:
            parts.append(
                f"Also flag as a custom concern - {rule.get('name')}: {rule.get('finding', '')}"
            )
        return "\n".join(parts)

    @classmethod
    def load(cls, path: Optional[str | Path] = None) -> "Playbook":
        p = Path(path) if path else DEFAULT_PLAYBOOK_PATH
        if not p.exists():
            return cls()
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(data)


def write_example_playbook(path: Optional[str | Path] = None) -> Path:
    p = Path(path) if path else DEFAULT_PLAYBOOK_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(EXAMPLE_PLAYBOOK, encoding="utf-8")
    return p
