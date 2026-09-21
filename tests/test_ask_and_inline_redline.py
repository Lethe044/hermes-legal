import pytest

from hermes_legal.ask import ask_contract, _keyword_search_answer
from hermes_legal.deadlines import extract_obligations
from hermes_legal.providers.offline_provider import OfflineProvider

TEXT = """
FREELANCE SERVICE AGREEMENT
This agreement is entered into on January 15, 2026 for a term of 2 years.
1. Termination. Either party may terminate this agreement with 15 day written notice.
2. Liability. Contractor's liability shall be uncapped and unlimited.
"""


def test_extract_obligations_finds_term_and_notice():
    obs = extract_obligations(TEXT)
    kinds = {o["kind"] for o in obs}
    assert "Contract Term" in kinds
    assert "Termination Notice Period" in kinds
    assert "Explicit Date Mentioned" in kinds


def test_keyword_search_answer_finds_relevant_paragraph():
    answer = _keyword_search_answer(TEXT, "what is the termination notice period?")
    assert "notice" in answer.lower()


def test_ask_contract_offline_uses_keyword_search():
    answer = ask_contract(TEXT, "termination notice", OfflineProvider())
    assert "notice" in answer.lower()


def test_write_redline_docx_inline(tmp_path):
    docx = pytest.importorskip("docx")
    from hermes_legal.reports.redline import write_redline_docx_inline

    docx_path = tmp_path / "contract.docx"
    d = docx.Document()
    d.add_paragraph("FREELANCE SERVICE AGREEMENT")
    d.add_paragraph("1. Termination. Either party may terminate this agreement with 2 day written notice.")
    d.add_paragraph("2. Liability. Contractor's liability shall be uncapped and unlimited.")
    d.save(str(docx_path))

    result = OfflineProvider().analyze(TEXT)
    out_path = tmp_path / "redlined.docx"
    saved = write_redline_docx_inline(docx_path, result, out_path)
    assert saved is not None and saved.exists()

    d2 = docx.Document(str(saved))
    xml = d2.element.xml
    assert "<w:ins " in xml
    assert 'w:author="Hermes Legal Advisor"' in xml
