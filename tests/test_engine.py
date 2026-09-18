from hermes_legal.analysis.engine import analyze_contract, compare_contracts, file_hash
from hermes_legal.memory.store import MemoryStore
from hermes_legal.providers.offline_provider import OfflineProvider

FREELANCE_V1 = """
FREELANCE SERVICE AGREEMENT between TechCorp Inc. and Contractor.
1. Termination. Either party may terminate this agreement with 2 day written notice.
2. Liability. Contractor's liability shall be uncapped and unlimited.
"""

FREELANCE_V2 = """
FREELANCE SERVICE AGREEMENT between TechCorp Inc. and Contractor.
1. Termination. Either party may terminate this agreement with 30 day written notice.
2. Liability. Contractor's liability shall be capped at 12 months of fees.
"""


def test_file_hash_is_stable():
    assert file_hash("abc") == file_hash("abc")
    assert file_hash("abc") != file_hash("abd")


def test_analyze_contract_writes_memory(tmp_path):
    memory = MemoryStore(base_dir=tmp_path)
    outcome = analyze_contract(FREELANCE_V1, provider=OfflineProvider(), memory=memory)

    assert outcome["result"].provider == "offline"
    assert len(memory.contracts()) == 1


def test_analyze_contract_no_save(tmp_path):
    memory = MemoryStore(base_dir=tmp_path)
    analyze_contract(FREELANCE_V1, provider=OfflineProvider(), memory=memory, save=False)
    assert len(memory.contracts()) == 0


def test_compare_contracts_detects_improvement():
    diff = compare_contracts(FREELANCE_V1, FREELANCE_V2, provider=OfflineProvider())
    statuses = {row["clause"]: row["status"] for row in diff["rows"]}
    assert statuses.get("Termination") == "IMPROVED"
    assert statuses.get("Liability") == "IMPROVED"
