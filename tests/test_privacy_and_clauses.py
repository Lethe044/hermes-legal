from hermes_legal.analysis.engine import analyze_contract
from hermes_legal.clause_library import MODEL_CLAUSES, attach_model_clauses
from hermes_legal.memory.store import MemoryStore
from hermes_legal.providers.base import AnalysisResult, BaseProvider
from hermes_legal.providers.offline_provider import OfflineProvider, RULES
from hermes_legal.redact import is_remote_provider, redact_text
from hermes_legal.reports.markdown import render_markdown_report

TEXT = (
    "FREELANCE SERVICE AGREEMENT between Acme Corp and Jane Doe. "
    "Contact jane.doe@example.com or +90 532 123 45 67. IBAN TR33 0006 1005 1978 6457 8413 26. "
    "1. Liability. Contractor's liability is uncapped and unlimited."
)


class RecordingProvider(BaseProvider):
    """Pretends to be a provider with a given name and records the text it was sent."""

    def __init__(self, name):
        self.name = name
        self.seen = None

    def is_available(self):
        return True

    def analyze(self, contract_text, perspective="neutral", language_hint=None, memory_context=""):
        self.seen = contract_text
        return AnalysisResult(contract_type="Test", parties="A and B", provider=self.name, clauses=[])


def test_redact_masks_common_sensitive_values():
    out, mapping = redact_text(TEXT, names=["Acme Corp", "Jane Doe"])
    assert "jane.doe@example.com" not in out
    assert "Acme Corp" not in out
    assert "Jane Doe" not in out
    assert "TR33" not in out
    assert "[EMAIL_1]" in out
    assert "[PARTY_1]" in out
    assert mapping["[EMAIL_1]"] == "jane.doe@example.com"


def test_redact_keeps_legal_terms_intact():
    out, _ = redact_text(TEXT, names=["Acme Corp"])
    assert "uncapped and unlimited" in out
    assert "Liability" in out


def test_redact_same_value_gets_same_placeholder():
    out, _ = redact_text("Mail a@b.co then again a@b.co", names=[])
    assert out.count("[EMAIL_1]") == 2


def test_is_remote_provider():
    assert is_remote_provider("groq")
    assert is_remote_provider("gemini")
    assert not is_remote_provider("ollama")
    assert not is_remote_provider("offline")


def test_engine_sends_redacted_text_only_to_remote_providers(tmp_path):
    remote = RecordingProvider("groq")
    analyze_contract(TEXT, provider=remote, memory=MemoryStore(base_dir=tmp_path / "a"),
                     redact=True, redact_names=["Acme Corp"])
    assert "jane.doe@example.com" not in remote.seen
    assert "Acme Corp" not in remote.seen

    local = RecordingProvider("ollama")
    analyze_contract(TEXT, provider=local, memory=MemoryStore(base_dir=tmp_path / "b"),
                     redact=True, redact_names=["Acme Corp"])
    assert "jane.doe@example.com" in local.seen


def test_engine_without_redact_sends_original(tmp_path):
    remote = RecordingProvider("groq")
    analyze_contract(TEXT, provider=remote, memory=MemoryStore(base_dir=tmp_path))
    assert "jane.doe@example.com" in remote.seen


def test_model_clause_library_covers_every_builtin_rule():
    for rule in RULES:
        assert rule["name"] in MODEL_CLAUSES, f"missing model clause for {rule['name']}"


def test_model_language_attached_only_to_flagged_clauses():
    clauses = [
        {"name": "Liability", "is_red_flag": True, "negotiation_suggestion": "cap it"},
        {"name": "Termination", "is_red_flag": False, "negotiation_suggestion": ""},
    ]
    out = attach_model_clauses(clauses)
    assert "model_language" in out[0]
    assert "model_language" not in out[1]


def test_markdown_report_includes_model_language(tmp_path):
    outcome = analyze_contract(TEXT, provider=OfflineProvider(), memory=MemoryStore(base_dir=tmp_path))
    md = render_markdown_report(outcome["result"], outcome["hash"], None)
    assert "Model language" in md


def test_hiring_side_perspective_softens_provider_bound_clause():
    neutral = OfflineProvider().analyze(TEXT, perspective="neutral")
    client = OfflineProvider().analyze(TEXT, perspective="client")
    n = next(c for c in neutral.clauses if c["name"] == "Liability")
    c = next(c for c in client.clauses if c["name"] == "Liability")
    assert c["score"] < n["score"]
    assert "Reviewing as client" in c["finding"]


def test_service_side_perspective_raises_payment_sensitivity():
    text = "SERVICE AGREEMENT. 1. Payment Terms. Client pays within net 30."
    neutral = OfflineProvider().analyze(text, perspective="neutral")
    contractor = OfflineProvider().analyze(text, perspective="contractor")
    n = next(c for c in neutral.clauses if c["name"] == "Payment Terms")
    c = next(c for c in contractor.clauses if c["name"] == "Payment Terms")
    assert c["score"] == n["score"] + 1


def test_cache_does_not_cross_perspectives(tmp_path):
    memory = MemoryStore(base_dir=tmp_path)
    first = analyze_contract(TEXT, provider=OfflineProvider(), memory=memory, perspective="neutral")
    other = analyze_contract(TEXT, provider=OfflineProvider(), memory=memory, perspective="client")
    again = analyze_contract(TEXT, provider=OfflineProvider(), memory=memory, perspective="client")
    assert first["from_cache"] is False
    assert other["from_cache"] is False
    assert again["from_cache"] is True


def test_redact_phone_formats_but_not_dates_or_amounts():
    text = (
        "Fee $85,000.00 due 2026-03-01; invoice 1234567. "
        "Call 0532 123 45 67 or (212) 555-0100 or +44 20 7946 0958."
    )
    out, mapping = redact_text(text)
    assert "$85,000.00" in out
    assert "2026-03-01" in out
    assert "1234567" in out
    assert out.count("[PHONE_") == 3


def test_redact_ids_and_cards():
    out, _ = redact_text("SSN 123-45-6789 and card 4111 1111 1111 1111.")
    assert "123-45-6789" not in out
    assert "4111" not in out
