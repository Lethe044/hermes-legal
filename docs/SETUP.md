# Setup Guide

## Requirements
Python 3.10+, OpenRouter API key (free at openrouter.ai)

## Install
pip install openai rich

## Configure
Windows:  set OPENROUTER_API_KEY=sk-or-...
Linux:    export OPENROUTER_API_KEY=sk-or-...

## Analyze a contract

Sample contracts included:
python demo/demo_legal.py --contract sample_contracts/freelance_contract.txt
python demo/demo_legal.py --contract sample_contracts/nda_contract.txt
python demo/demo_legal.py --contract sample_contracts/employment_contract.txt

Your own contract (must be .txt):
python demo/demo_legal.py --contract path/to/your_contract.txt

## Output
Reports: ~/.hermes/legal/reports/
Memory:  ~/.hermes/legal/contracts_memory.jsonl

## Disclaimer
This tool provides analysis, not legal advice.
Always consult a qualified attorney before signing.
