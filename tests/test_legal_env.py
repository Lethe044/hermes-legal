"""Tests for Hermes Legal Advisor environment and reward function."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from environments.legal_env import (
    LegalAdvisorEnv, LegalScenario, SCENARIOS, compute_legal_reward
)


class TestScenarios:
    def test_count(self):
        assert len(SCENARIOS) >= 4

    def test_fields(self):
        for s in SCENARIOS:
            assert s.id
            assert s.contract_type
            assert s.title
            assert s.expected_risk in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
            assert s.difficulty in ("easy", "medium", "hard")

    def test_risk_levels_covered(self):
        levels = {s.expected_risk for s in SCENARIOS}
        assert "CRITICAL" in levels
        assert "LOW" in levels


class TestEnv:
    def setup_method(self):
        self.env = LegalAdvisorEnv()

    def test_get_next_item(self):
        s = self.env.get_next_item()
        assert isinstance(s, LegalScenario)

    def test_format_prompt(self):
        s = self.env.get_next_item()
        p = self.env.format_prompt(s)
        assert len(p) > 30
        assert s.contract_type in p

    def test_cycling(self):
        ids = [self.env.get_next_item().id for _ in range(len(SCENARIOS) * 2)]
        assert len(set(ids)) == len(SCENARIOS)

    def test_evaluate(self):
        s = self.env.get_next_item()
        r = self.env.evaluate({"output": "", "tool_calls": []}, s)
        assert "total_reward" in r
        assert 0.0 <= r["total_reward"] <= 1.0


class TestRewardFunction:
    def _traj(self, tools, output=""):
        return {"output": output, "tool_calls": [{"name": t, "input": {}} for t in tools]}

    def test_perfect_critical(self):
        r = compute_legal_reward(
            {"output": "critical uncapped liability non-compete 3 years worldwide 2 days termination ip personal time indefinite confidentiality",
             "tool_calls": [
                 {"name": "read_contract", "input": {}},
                 {"name": "search_memory", "input": {}},
                 {"name": "score_clause", "input": {"clause_name": "Termination", "score": 9}},
                 {"name": "score_clause", "input": {"clause_name": "Liability", "score": 10}},
                 {"name": "score_clause", "input": {"clause_name": "Non-Compete", "score": 9}},
                 {"name": "score_clause", "input": {"clause_name": "IP Ownership", "score": 9}},
                 {"name": "score_clause", "input": {"clause_name": "Confidentiality", "score": 8}},
                 {"name": "score_clause", "input": {"clause_name": "Payment Terms", "score": 4}},
                 {"name": "score_clause", "input": {"clause_name": "Governing Law", "score": 3}},
                 {"name": "send_alert", "input": {}},
                 {"name": "save_report", "input": {}},
             ]},
            SCENARIOS[0]
        )
        assert r["total"] >= 0.80
        assert r["contract_read"] == 0.15
        assert r["report_saved"] == 0.20
        assert r["clauses_scored"] == 0.30

    def test_no_report(self):
        r = compute_legal_reward(self._traj(["read_contract", "score_clause"]), SCENARIOS[0])
        assert r["report_saved"] == 0.0

    def test_no_contract_read(self):
        r = compute_legal_reward(self._traj(["score_clause", "save_report"]), SCENARIOS[0])
        assert r["contract_read"] == 0.0

    def test_partial_scoring(self):
        r = compute_legal_reward(self._traj(["read_contract", "score_clause", "score_clause", "score_clause", "save_report"]), SCENARIOS[0])
        assert r["clauses_scored"] == 0.18

    def test_total_in_range(self):
        r = compute_legal_reward(self._traj([]), SCENARIOS[0])
        assert 0.0 <= r["total"] <= 1.0


class TestDemoScript:
    def test_file_exists(self):
        assert Path("demo/demo_legal.py").exists()

    def test_syntax(self):
        import ast
        src = Path("demo/demo_legal.py").read_text(encoding="utf-8")
        ast.parse(src)

    def test_sample_contracts_exist(self):
        assert Path("sample_contracts/freelance_contract.txt").exists()
        assert Path("sample_contracts/nda_contract.txt").exists()
        assert Path("sample_contracts/employment_contract.txt").exists()

    def test_skill_md_exists(self):
        assert Path("skills/legal-advisor/SKILL.md").exists()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
