from pathlib import Path

from hermes_legal.analysis.engine import analyze_contract
from hermes_legal.extract import extract_key_terms, extract_parties
from hermes_legal.memory.store import MemoryStore
from hermes_legal.providers.offline_provider import OfflineProvider, guess_contract_type

SAMPLES = Path(__file__).parent.parent / "sample_contracts"


def _flags(text, perspective="neutral"):
    r = OfflineProvider().analyze(text, perspective=perspective)
    return {c["name"]: c for c in r.clauses if c["is_red_flag"]}, r


# ---------- party and key term extraction ----------

def test_parties_from_sample_contracts():
    assert extract_parties((SAMPLES / "nda_contract.txt").read_text(encoding="utf-8")) == \
        "Alpha Ventures LLC and Beta Solutions Ltd"
    assert extract_parties((SAMPLES / "employment_contract.txt").read_text(encoding="utf-8")) == \
        "StartupXYZ Inc. and Jane Smith"


def test_party_falls_back_to_defined_role_when_second_party_is_unnamed():
    text = (SAMPLES / "freelance_contract.txt").read_text(encoding="utf-8")
    assert extract_parties(text) == "TechCorp Inc. and Contractor"


def test_parties_in_other_languages():
    tr = 'İŞ SÖZLEŞMESİ\nİşbu sözleşme Acme A.Ş. ("İşveren") ile Ayşe Yılmaz ("Çalışan") arasında imzalanmıştır.'
    es = 'CONTRATO\nEste contrato se celebra entre Iberia Tech S.L. ("Cliente") y Juan Pérez ("Contratista").'
    de = 'VERTRAG\nDieser Vertrag wird geschlossen zwischen Berlin GmbH ("Auftraggeber") und Max Mustermann ("Auftragnehmer").'
    assert extract_parties(tr) == "Acme A.Ş. and Ayşe Yılmaz"
    assert extract_parties(es) == "Iberia Tech S.L. and Juan Pérez"
    assert extract_parties(de) == "Berlin GmbH and Max Mustermann"


def test_parties_none_when_not_found():
    assert extract_parties("Some random text without any parties.") is None


def test_key_terms_from_freelance_sample():
    terms = extract_key_terms((SAMPLES / "freelance_contract.txt").read_text(encoding="utf-8"))
    assert terms["Effective date"] == "2026-01-01"
    assert "$85 per hour" in terms["Amounts"]
    assert terms["Payment due"] == "within 60 days"
    assert terms["Governing law"].startswith("Delaware")


def test_key_terms_do_not_invent_values():
    assert extract_key_terms("Nothing useful here.") == {}


def test_offline_result_carries_parties_and_terms(tmp_path):
    text = (SAMPLES / "nda_contract.txt").read_text(encoding="utf-8")
    r = OfflineProvider().analyze(text)
    assert r.parties == "Alpha Ventures LLC and Beta Solutions Ltd"
    assert r.key_terms["Governing law"] == "England and Wales"


def test_trend_works_offline_now_that_parties_are_extracted(tmp_path):
    memory = MemoryStore(base_dir=tmp_path)
    v1 = (SAMPLES / "freelance_contract.txt").read_text(encoding="utf-8")
    v2 = (SAMPLES / "freelance_contract_v2.txt").read_text(encoding="utf-8")
    analyze_contract(v1, provider=OfflineProvider(), memory=memory)
    second = analyze_contract(v2, provider=OfflineProvider(), memory=memory)
    assert second["trend"] in {"IMPROVED", "WORSE", "UNCHANGED"}


# ---------- missing clause detection ----------

def test_nda_sample_is_not_reported_missing_clauses_it_contains():
    r = OfflineProvider().analyze((SAMPLES / "nda_contract.txt").read_text(encoding="utf-8"))
    assert r.missing_clauses == []


def test_genuinely_missing_clause_is_still_reported():
    text = "FREELANCE SERVICE AGREEMENT. The Contractor will build a website for the Client."
    r = OfflineProvider().analyze(text)
    assert "liability" in r.missing_clauses
    assert "confidentiality" in r.missing_clauses


# ---------- contract type scoring ----------

def test_word_standard_does_not_make_a_contract_an_nda():
    assert guess_contract_type("SERVICE AGREEMENT. Standard rates apply and the agenda is attached.") == "Service Agreement"


def test_contractor_not_an_employee_is_not_employment():
    text = "CONSULTING AGREEMENT. Contractor is not an employee of Client."
    assert guess_contract_type(text) == "Freelance Service Agreement"


def test_lease_and_saas_types():
    assert guess_contract_type("LEASE AGREEMENT between Landlord and Tenant. Rent due monthly.") == "Lease Agreement"
    assert guess_contract_type("SOFTWARE AS A SERVICE AGREEMENT. Subscription fees apply.") == "Software / SaaS License"


# ---------- new rules ----------

def test_indemnification_flagged_when_broad():
    flags, _ = _flags("1. Indemnification. Contractor shall indemnify Client against any and all claims, losses and damages.")
    assert "Indemnification" in flags


def test_indemnification_not_flagged_when_limited():
    flags, r = _flags("1. Indemnification. Each party shall indemnify the other for third-party claims caused by its breach.")
    assert "Indemnification" not in flags
    assert any(c["name"] == "Indemnification" for c in r.clauses)


def test_unilateral_amendment_flagged():
    flags, _ = _flags("Provider may modify these terms at any time without notice.")
    assert "Amendment" in flags


def test_amendment_in_writing_not_flagged():
    flags, _ = _flags("This Agreement may be amended only by a written document signed by both parties.")
    assert "Amendment" not in flags


def test_assignment_without_consent_flagged_but_normal_restriction_is_not():
    flagged, _ = _flags("Client may assign this Agreement to any third party without consent.")
    normal, _ = _flags("Neither party may assign this Agreement without the other party's written consent.")
    assert "Assignment" in flagged
    assert "Assignment" not in normal


def test_exclusivity_flagged():
    flags, _ = _flags("Contractor shall work exclusively for Client during the term.")
    assert "Exclusivity" in flags


def test_non_solicitation_only_flagged_beyond_two_years():
    long_term, _ = _flags("Contractor shall not solicit Client's employees for 5 years after termination.")
    short_term, _ = _flags("Contractor shall not solicit Client's employees for 1 year after termination.")
    assert "Non-Solicitation" in long_term
    assert "Non-Solicitation" not in short_term


def test_penalties_flagged_for_daily_rates_not_monthly_interest():
    daily, _ = _flags("Liquidated damages of 2% per day apply for each day of delay.")
    interest, _ = _flags("Late invoices accrue a penalty interest of 1.5% per month.")
    assert "Penalties" in daily
    assert "Penalties" not in interest


def test_warranty_as_is_flagged():
    flags, _ = _flags("The deliverables are provided as is, and Contractor disclaims all warranties.")
    assert "Warranty" in flags


def test_data_protection_sharing_flagged():
    flags, _ = _flags("Provider may share personal data with third parties for any purpose.")
    assert "Data Protection" in flags


def test_force_majeure_detected_but_not_a_red_flag():
    flags, r = _flags("Neither party is liable for events of force majeure.")
    assert "Force Majeure" not in flags
    assert any(c["name"] == "Force Majeure" for c in r.clauses)


def test_new_rules_work_in_turkish():
    flags, _ = _flags("Yüklenici tüm zararları tazmin etmeyi kabul eder. Sözleşme tek taraflı olarak değiştirilebilir.")
    assert "Indemnification" in flags
    assert "Amendment" in flags


# ---------- overall risk floor ----------

def test_single_critical_clause_cannot_hide_behind_many_harmless_ones():
    text = (
        "SERVICE AGREEMENT. Termination requires 30 days written notice. "
        "Confidentiality lasts 3 years. Payment is net 30. Governing law: Delaware. "
        "Warranty applies for 90 days. Force majeure applies. "
        "Contractor's liability is uncapped and unlimited."
    )
    r = OfflineProvider().analyze(text)
    assert max(c["score"] for c in r.clauses) >= 9
    assert r.overall_risk in {"HIGH", "CRITICAL"}


def test_clean_contract_stays_low():
    text = (
        "SERVICE AGREEMENT. Either party may terminate with 30 days written notice. "
        "Liability is capped at fees paid. Confidentiality lasts 3 years. Governed by the laws of Delaware."
    )
    r = OfflineProvider().analyze(text)
    assert r.overall_risk == "LOW"
    assert r.verdict == "SIGN"


# ---------- engine fills gaps left by a provider ----------

def test_engine_fills_missing_parties_and_terms_but_keeps_provider_values(tmp_path):
    from hermes_legal.providers.base import AnalysisResult, BaseProvider

    class Sparse(BaseProvider):
        name = "groq"
        def is_available(self): return True
        def analyze(self, contract_text, perspective="neutral", language_hint=None, memory_context=""):
            return AnalysisResult(contract_type="X", parties="Unknown", provider="groq",
                                  key_terms={"Governing law": "Provider says Narnia"})

    text = (SAMPLES / "nda_contract.txt").read_text(encoding="utf-8")
    outcome = analyze_contract(text, provider=Sparse(), memory=MemoryStore(base_dir=tmp_path))
    result = outcome["result"]
    assert result.parties == "Alpha Ventures LLC and Beta Solutions Ltd"
    assert result.key_terms["Governing law"] == "Provider says Narnia"
    assert result.key_terms["Effective date"] == "2026-03-01"
