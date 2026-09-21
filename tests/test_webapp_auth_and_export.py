import zipfile

from hermes_legal.analysis.engine import analyze_contract
from hermes_legal.memory.store import MemoryStore
from hermes_legal.providers.offline_provider import OfflineProvider
from hermes_legal.providers import AnalysisResult
from hermes_legal.reports.markdown import render_markdown_report

TEXT = "FREELANCE SERVICE AGREEMENT between TechCorp and Contractor. 1. Liability. Uncapped and unlimited liability."


def test_webapp_auth_check_no_key_always_authorized():
    from hermes_legal.webapp import _Handler

    class FakeHandler(_Handler):
        def __init__(self):
            self.path = "/api/history"
            self.headers = {}

    h = FakeHandler()
    h.api_key = None
    assert h._is_authorized() is True


def test_webapp_auth_check_with_header():
    from hermes_legal.webapp import _Handler

    class FakeHandler(_Handler):
        def __init__(self, headers):
            self.path = "/api/history"
            self.headers = headers

    h = FakeHandler({"X-API-Key": "secret"})
    h.api_key = "secret"
    assert h._is_authorized() is True

    h2 = FakeHandler({"X-API-Key": "wrong"})
    h2.api_key = "secret"
    assert h2._is_authorized() is False


def test_webapp_auth_check_with_query_param():
    from hermes_legal.webapp import _Handler

    class FakeHandler(_Handler):
        def __init__(self, path):
            self.path = path
            self.headers = {}

    h = FakeHandler("/api/history?key=secret")
    h.api_key = "secret"
    assert h._is_authorized() is True


def test_export_bundle_contains_expected_files(tmp_path):
    memory = MemoryStore(base_dir=tmp_path)
    analyze_contract(TEXT, provider=OfflineProvider(), memory=memory, client="Acme Corp")

    contracts = [c for c in memory.contracts() if c.get("full_result")]
    assert len(contracts) == 1

    out_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, c in enumerate(contracts, 1):
            result = AnalysisResult(**c["full_result"])
            report_md = render_markdown_report(result, c.get("contract_hash", ""), None)
            zf.writestr(f"{i:02d}_report.md", report_md)

    with zipfile.ZipFile(out_path) as zf:
        names = zf.namelist()
        assert "01_report.md" in names
        content = zf.read("01_report.md").decode("utf-8")
        assert "Legal Analysis Report" in content
