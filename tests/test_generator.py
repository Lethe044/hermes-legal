from hermes_legal.generator import CONTRACT_TEMPLATES, generate_contract


def test_all_templates_have_name_and_fields():
    for key, tpl in CONTRACT_TEMPLATES.items():
        assert tpl["name"]
        assert tpl["fields"]
        assert "{" in tpl["body"]


def test_generate_contract_fills_provided_fields():
    text = generate_contract("nda", {"party_a": "Acme Inc.", "party_b": "Beta LLC"})
    assert "Acme Inc." in text
    assert "Beta LLC" in text


def test_generate_contract_placeholders_for_missing_fields():
    text = generate_contract("nda", {})
    assert "[PARTY A]" in text
    assert "[EFFECTIVE DATE]" in text
