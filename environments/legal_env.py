"""
Hermes Legal Advisor — Atropos RL Environment
===============================================
Trains Hermes to be a better contract analyst:
thorough, accurate, and actionable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from atropos.environments.base import HermesAgentBaseEnv
except ImportError:
    class HermesAgentBaseEnv:
        pass


@dataclass
class LegalScenario:
    id: str
    contract_type: str
    title: str
    description: str
    red_flags: List[str]
    expected_risk: str
    difficulty: str = "medium"


SCENARIOS: List[LegalScenario] = [
    LegalScenario(
        id="freelance-high-risk",
        contract_type="Freelance Service Agreement",
        title="Highly unfavorable freelance contract",
        description="Contract with 2-day termination, uncapped contractor liability, worldwide 3-year non-compete, indefinite confidentiality, IP covering personal time.",
        red_flags=["2 days termination", "uncapped liability", "worldwide non-compete 3 years", "indefinite confidentiality", "IP personal time"],
        expected_risk="CRITICAL",
        difficulty="medium",
    ),
    LegalScenario(
        id="nda-balanced",
        contract_type="Mutual NDA",
        title="Balanced mutual NDA",
        description="Mutual NDA with reasonable 2-year term, standard exclusions, both parties protected equally.",
        red_flags=[],
        expected_risk="LOW",
        difficulty="easy",
    ),
    LegalScenario(
        id="employment-standard",
        contract_type="Employment Agreement",
        title="Standard employment agreement",
        description="At-will employment with 12-month non-compete, standard IP assignment, reasonable benefits.",
        red_flags=["ip personal time", "at-will no severance"],
        expected_risk="MEDIUM",
        difficulty="easy",
    ),
    LegalScenario(
        id="service-uncapped-liability",
        contract_type="Service Agreement",
        title="Service agreement with uncapped liability",
        description="Service contract where service provider has unlimited liability but client capped at 1 month fees.",
        red_flags=["uncapped liability", "asymmetric liability cap"],
        expected_risk="HIGH",
        difficulty="medium",
    ),
    LegalScenario(
        id="saas-auto-renewal",
        contract_type="SaaS Subscription Agreement",
        title="SaaS contract with predatory auto-renewal",
        description="SaaS agreement with 7-day cancellation window, auto-renewal, price escalation clause.",
        red_flags=["7 day cancellation window", "auto-renewal", "price escalation"],
        expected_risk="HIGH",
        difficulty="hard",
    ),
]


def compute_legal_reward(
    trajectory: Dict[str, Any],
    scenario: LegalScenario,
) -> Dict[str, float]:
    """
    Reward function for Hermes Legal Advisor.

    Components:
        contract_read      (15%) — Did it read the contract?
        clauses_scored     (30%) — Did it score multiple clause categories?
        red_flags_found    (25%) — Did it identify the expected red flags?
        report_saved       (20%) — Did it save a structured report?
        risk_accurate      (10%) — Was the overall risk level correct?
    """
    output     = trajectory.get("output", "").lower()
    tool_calls = trajectory.get("tool_calls", [])
    tool_names = [tc.get("name", "") for tc in tool_calls]
    rewards: Dict[str, float] = {}

    # 1. Contract read (15%)
    rewards["contract_read"] = 0.15 if "read_contract" in tool_names else 0.0

    # 2. Clauses scored (30%)
    score_calls = sum(1 for n in tool_names if n == "score_clause")
    if score_calls >= 7:
        rewards["clauses_scored"] = 0.30
    elif score_calls >= 4:
        rewards["clauses_scored"] = 0.18
    elif score_calls >= 1:
        rewards["clauses_scored"] = 0.08
    else:
        rewards["clauses_scored"] = 0.0

    # 3. Red flags found (25%)
    if scenario.red_flags:
        found = sum(
            1 for rf in scenario.red_flags
            if any(word in output for word in rf.lower().split()[:2])
        )
        rewards["red_flags_found"] = round(0.25 * (found / len(scenario.red_flags)), 4)
    else:
        # If no red flags expected, reward for correctly NOT raising false alarms
        alerts = sum(1 for n in tool_names if n == "send_alert")
        rewards["red_flags_found"] = 0.25 if alerts == 0 else 0.10

    # 4. Report saved (20%)
    rewards["report_saved"] = 0.20 if "save_report" in tool_names else 0.0

    # 5. Risk level accurate (10%)
    expected = scenario.expected_risk.lower()
    if expected in output:
        rewards["risk_accurate"] = 0.10
    elif (expected == "critical" and "high" in output) or \
         (expected == "high" and "critical" in output):
        rewards["risk_accurate"] = 0.05  # Close enough
    else:
        rewards["risk_accurate"] = 0.0

    rewards["total"] = round(sum(rewards.values()), 4)
    return rewards


class LegalAdvisorEnv(HermesAgentBaseEnv):
    """Atropos RL environment for Hermes Legal Advisor."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._scenarios = SCENARIOS * 3
        self._idx = 0

    def get_next_item(self) -> LegalScenario:
        s = self._scenarios[self._idx % len(self._scenarios)]
        self._idx += 1
        return s

    def format_prompt(self, scenario: LegalScenario) -> str:
        return (
            f"Contract type: {scenario.contract_type}\n"
            f"Task: {scenario.title}\n\n"
            f"Contract description: {scenario.description}\n\n"
            f"Run the full analysis pipeline: read, score all clauses, "
            f"compare with memory, send alert if needed, save report."
        )

    def evaluate(self, trajectory: Dict[str, Any], scenario: LegalScenario) -> Dict[str, Any]:
        rewards = compute_legal_reward(trajectory, scenario)
        return {
            "rewards":      rewards,
            "total_reward": rewards["total"],
            "scenario_id":  scenario.id,
            "difficulty":   scenario.difficulty,
        }


def smoke_test():
    print("Running LegalAdvisorEnv smoke test...")
    env = LegalAdvisorEnv()

    for i in range(len(SCENARIOS)):
        s = env.get_next_item()
        p = env.format_prompt(s)
        assert len(p) > 30
        print(f"  ✓ {s.id}")

    mock_trajectory = {
        "output": "freelance service agreement techcorp contractor critical risk uncapped liability non-compete 3 years worldwide ip personal time 2 days termination indefinite confidentiality",
        "tool_calls": [
            {"name": "read_contract",    "input": {"path": "freelance.txt"}},
            {"name": "search_memory",    "input": {"query": "TechCorp"}},
            {"name": "score_clause",     "input": {"clause_name": "Termination", "score": 9}},
            {"name": "score_clause",     "input": {"clause_name": "Liability", "score": 10}},
            {"name": "score_clause",     "input": {"clause_name": "Non-Compete", "score": 9}},
            {"name": "score_clause",     "input": {"clause_name": "Confidentiality", "score": 8}},
            {"name": "score_clause",     "input": {"clause_name": "IP Ownership", "score": 9}},
            {"name": "score_clause",     "input": {"clause_name": "Payment Terms", "score": 4}},
            {"name": "score_clause",     "input": {"clause_name": "Governing Law", "score": 3}},
            {"name": "send_alert",       "input": {"risk_level": "CRITICAL", "message": "Multiple red flags"}},
            {"name": "save_report",      "input": {"contract_type": "Freelance", "risk_level": "CRITICAL"}},
        ],
    }
    rewards = compute_legal_reward(mock_trajectory, SCENARIOS[0])
    print(f"\n  Reward breakdown:")
    for k, v in rewards.items():
        print(f"    {k}: {v}")
    assert rewards["total"] >= 0.80
    print(f"\n  Total: {rewards['total']} ✓")
    print("\nAll smoke tests passed!")


if __name__ == "__main__":
    smoke_test()
