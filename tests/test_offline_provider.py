from hermes_legal.providers.offline_provider import OfflineProvider, detect_language, guess_contract_type


SAMPLE_HIGH_RISK = """
FREELANCE SERVICE AGREEMENT

This Freelance Service Agreement is entered into between TechCorp Inc. and the Contractor.

1. Termination. Either party may terminate this agreement with 2 day written notice.

2. Liability. Contractor's liability under this agreement shall be uncapped and unlimited.

3. Intellectual Property. All work product created by Contractor, including any work
created on personal time, shall be owned exclusively by TechCorp.

4. Non-Compete. Contractor agrees to a worldwide non-compete for a period of 3 years.

5. Confidentiality. Contractor's confidentiality obligations shall survive perpetually.

6. Payment Terms. TechCorp shall pay Contractor within net 90 days of invoice.
"""

SAMPLE_LOW_RISK = """
MUTUAL NON-DISCLOSURE AGREEMENT

This NDA is between Acme Co. and Beta LLC.

1. Definition of Confidential Information. Confidential information means non-public
business information disclosed by either party.

2. Term. This agreement's confidentiality obligations survive for 3 years after disclosure.

3. Governing Law. This agreement is governed by the laws of the State of Delaware.
"""


def test_detect_language_english():
    assert detect_language(SAMPLE_HIGH_RISK) == "EN"


def test_detect_language_spanish():
    text = "CONTRATO DE SERVICIOS. Las partes acuerdan el pago del contratista por el servicio."
    assert detect_language(text) == "ES"


def test_detect_language_german():
    text = "Dieser Vertrag zwischen Auftragnehmer und Kunde regelt die Zahlung fuer die Dienstleistung."
    assert detect_language(text) == "DE"


def test_guess_contract_type():
    assert guess_contract_type(SAMPLE_HIGH_RISK) == "Freelance Service Agreement"
    assert guess_contract_type(SAMPLE_LOW_RISK) == "NDA"


def test_offline_provider_is_always_available():
    provider = OfflineProvider()
    assert provider.is_available() is True


def test_offline_provider_flags_known_red_flags():
    provider = OfflineProvider()
    result = provider.analyze(SAMPLE_HIGH_RISK)

    flagged_names = {c["name"] for c in result.clauses if c["is_red_flag"]}
    assert "Termination" in flagged_names
    assert "Liability" in flagged_names
    assert "Non-Compete" in flagged_names
    assert result.overall_risk in ("HIGH", "CRITICAL")
    assert result.verdict in ("NEGOTIATE", "REJECT")


def test_offline_provider_low_risk_contract():
    provider = OfflineProvider()
    result = provider.analyze(SAMPLE_LOW_RISK)
    red_flags = [c for c in result.clauses if c["is_red_flag"]]
    assert len(red_flags) == 0
