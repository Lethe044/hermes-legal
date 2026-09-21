from hermes_legal.analysis.engine import analyze_contract
from hermes_legal.memory.store import MemoryStore
from hermes_legal.providers.offline_provider import OfflineProvider
from hermes_legal.reports.portfolio import build_portfolio_stats, render_portfolio_dashboard

TEXT_A = "FREELANCE SERVICE AGREEMENT between TechCorp and Contractor. 1. Liability. Uncapped and unlimited liability."
TEXT_B = "MUTUAL NON-DISCLOSURE AGREEMENT between Acme and Beta LLC. 1. Confidentiality survives perpetually."


def test_second_analysis_of_same_text_uses_cache(tmp_path):
    memory = MemoryStore(base_dir=tmp_path)
    first = analyze_contract(TEXT_A, provider=OfflineProvider(), memory=memory)
    second = analyze_contract(TEXT_A, provider=OfflineProvider(), memory=memory)
    assert first["from_cache"] is False
    assert second["from_cache"] is True
    assert second["result"].overall_risk == first["result"].overall_risk


def test_force_bypasses_cache(tmp_path):
    memory = MemoryStore(base_dir=tmp_path)
    analyze_contract(TEXT_A, provider=OfflineProvider(), memory=memory)
    forced = analyze_contract(TEXT_A, provider=OfflineProvider(), memory=memory, force=True)
    assert forced["from_cache"] is False


def test_no_cache_flag_skips_cache(tmp_path):
    memory = MemoryStore(base_dir=tmp_path)
    analyze_contract(TEXT_A, provider=OfflineProvider(), memory=memory)
    no_cache = analyze_contract(TEXT_A, provider=OfflineProvider(), memory=memory, use_cache=False)
    assert no_cache["from_cache"] is False


def test_portfolio_stats_aggregate_across_contracts(tmp_path):
    memory = MemoryStore(base_dir=tmp_path)
    analyze_contract(TEXT_A, provider=OfflineProvider(), memory=memory)
    analyze_contract(TEXT_B, provider=OfflineProvider(), memory=memory)

    contracts = memory.contracts()
    assert len(contracts) == 2
    stats = build_portfolio_stats(contracts)
    assert "Liability" in dict(stats["top_flags"])
    # offline provider doesn't extract named parties, so both contracts
    # share the same placeholder "parties" value and group together
    assert sum(e["count"] for e in stats["by_party"].values()) == 2


def test_render_portfolio_dashboard_produces_html(tmp_path):
    memory = MemoryStore(base_dir=tmp_path)
    analyze_contract(TEXT_A, provider=OfflineProvider(), memory=memory)
    html = render_portfolio_dashboard(memory.contracts())
    assert "<html" in html
    assert "Portfolio Dashboard" in html
