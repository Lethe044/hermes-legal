from hermes_legal.playbook import Playbook, write_example_playbook
from hermes_legal.providers.offline_provider import OfflineProvider

HIGH_RISK = """
FREELANCE SERVICE AGREEMENT
1. Non-Compete. Contractor agrees to a worldwide non-compete for a period of 3 years.
"""


def test_empty_playbook_has_defaults():
    pb = Playbook()
    assert pb.firm_name is None
    assert pb.thresholds == {"critical": 8, "high": 7, "medium": 4}
    assert pb.rule_overrides == {}
    assert pb.custom_rules == []


def test_write_example_playbook(tmp_path):
    path = write_example_playbook(tmp_path / "playbook.yaml")
    assert path.exists()
    pb = Playbook.load(path)
    assert pb.firm_name == "Your Firm Name"
    assert "Non-Compete" in pb.rule_overrides
    assert len(pb.custom_rules) == 1


def test_playbook_overrides_offline_provider_score(tmp_path):
    path = write_example_playbook(tmp_path / "playbook.yaml")
    pb = Playbook.load(path)
    provider = OfflineProvider(playbook=pb)
    result = provider.analyze(HIGH_RISK)
    noncompete = next(c for c in result.clauses if c["name"] == "Non-Compete")
    assert noncompete["score"] == 10


def test_missing_playbook_file_returns_empty():
    pb = Playbook.load("/nonexistent/path/playbook.yaml")
    assert pb.firm_name is None
