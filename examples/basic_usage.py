"""
Example: using Hermes Legal Advisor as a library instead of the CLI.

Run with:  python examples/basic_usage.py
"""

from pathlib import Path

from hermes_legal.analysis.engine import analyze_contract
from hermes_legal.ingest import read_document
from hermes_legal.providers import get_provider
from hermes_legal.reports import render_markdown_report

CONTRACT_PATH = Path(__file__).parent.parent / "sample_contracts" / "freelance_contract.txt"


def main():
    text = read_document(CONTRACT_PATH)

    # "auto" picks Groq/Gemini/OpenRouter/Ollama if configured, otherwise
    # falls back to the offline rule engine - no API key required to run
    # this example.
    provider = get_provider("auto")
    print(f"Using provider: {provider.name}\n")

    outcome = analyze_contract(text, provider=provider, perspective="contractor")
    result = outcome["result"]

    print(f"Contract type : {result.contract_type}")
    print(f"Overall risk  : {result.overall_risk}")
    print(f"Verdict       : {result.verdict}")
    print(f"Red flags     : {len(outcome['red_flags'])}")
    print()

    report = render_markdown_report(result, outcome["hash"], outcome["trend"])
    out_path = Path("example_report.md")
    out_path.write_text(report, encoding="utf-8")
    print(f"Full report written to {out_path.resolve()}")


if __name__ == "__main__":
    main()
