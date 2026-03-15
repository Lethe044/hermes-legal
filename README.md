# Hermes Legal Advisor ⚖️

**Autonomous contract analysis agent that reads what you might miss.**

> Built for the NousResearch "Show us what Hermes Agent can do" hackathon.

Contracts are dense, tedious, and full of clauses that sound reasonable until a lawyer
tells you they aren't. Hermes Legal Advisor reads every clause, scores every risk,
suggests negotiation language, gives you a final verdict, and remembers every
contract it has ever analyzed - in English and Turkish.

## What It Does

Feed it a contract. It reads the full document, scores each clause for risk,
flags red flags, suggests how to rewrite problematic clauses, checks for missing
standard clauses, compares against previously analyzed contracts, and delivers
a final **SIGN / NEGOTIATE / REJECT** verdict.

**The more contracts you analyze, the smarter it gets at spotting patterns.**

## Architecture

```mermaid
flowchart TD
    A([📄 Contract File]) --> B
    B[📖 INGEST<br/>Read + detect language<br/>EN or TR] --> C
    C[🔍 MEMORY CHECK<br/>Prior contracts<br/>from same party?] --> D
    D[⚖️ SCORE CLAUSES<br/>9 categories<br/>Risk 1-10 each] --> E
    E[🔎 CHECK MISSING<br/>Standard clauses<br/>present?] --> F
    F[💬 NEGOTIATE<br/>Suggest rewrite for<br/>top 3 critical clauses] --> G
    G{Overall Risk?}
    G -- CRITICAL/HIGH --> H[🚨 ALERT<br/>Gateway notification]
    G --> I[🏛️ VERDICT<br/>SIGN / NEGOTIATE<br/>/ REJECT]
    H --> I
    I --> J([💾 SAVE REPORT<br/>Archive to Memory<br/>Pattern detection])

    style A fill:#2980b9,color:#fff
    style H fill:#c0392b,color:#fff
    style I fill:#27ae60,color:#fff
    style J fill:#8e44ad,color:#fff
```

## Hermes Features Used

| Feature | How It's Used |
|---------|--------------|
| **Memory** | Stores every analyzed contract - detects if counter-party terms are getting worse |
| **Skills** | Legal playbook defines scoring rubric, red flags, and verdict logic |
| **Subagents** | Parallel clause scoring - each category analyzed independently |
| **Gateway** | Sends CRITICAL/HIGH alerts (extensible to email/Slack/Telegram) |
| **Atropos RL** | Reward function trains Hermes to find more red flags with higher accuracy |

## Key Features

| Feature | Description |
|---------|-------------|
| 🌐 **Bilingual** | English and Turkish contract analysis |
| ⚖️ **9-Clause Scoring** | Every clause scored 1-10 with reasoning |
| 💬 **Negotiation Text** | Suggests how to rewrite critical clauses |
| 🔎 **Missing Clause Detection** | Flags standard clauses that are absent |
| 🏛️ **Final Verdict** | SIGN / NEGOTIATE / REJECT with reasoning |
| 🧠 **Memory** | Compares against all prior contracts from same party |
| 💬 **Chat Mode** | Ask questions about clauses and past analyses |

## Risk Scoring

| Score | Level | Meaning |
|-------|-------|---------|
| 9-10 | 🔴 CRITICAL | Red flag - potentially unacceptable |
| 7-8 | 🟠 HIGH | Significantly unfavorable - negotiate |
| 5-6 | 🟡 MEDIUM | Worth noting - review carefully |
| 1-4 | 🟢 LOW | Standard and acceptable |

## Automatic Red Flags

- Termination notice < 7 days (one party only)
- Uncapped liability on one party only
- IP assignment covering personal-time work
- Non-compete > 2 years or worldwide scope
- Auto-renewal with < 30 days cancellation window
- Arbitration costs borne entirely by one party

## Quick Start

```bash
pip install openai rich
set OPENROUTER_API_KEY=sk-or-...

python demo/demo_legal.py --contract sample_contracts/freelance_contract.txt
python demo/demo_legal.py --contract sample_contracts/nda_contract.txt
python demo/demo_legal.py --contract sample_contracts/employment_contract.txt
python demo/demo_legal.py --turkish
python demo/demo_legal.py --chat
```

## Reward Function

```mermaid
pie title Legal Advisor Reward Components
    "Clauses Scored - All 9 categories?" : 30
    "Red Flags Found - Identified correctly?" : 25
    "Report Saved - Structured output?" : 20
    "Contract Read - Full document loaded?" : 15
    "Risk Accurate - Correct overall level?" : 10
```

## Project Structure

```mermaid
graph LR
    A[hermes-legal] --> B[skills/]
    A --> C[environments/]
    A --> D[demo/]
    A --> E[tests/]
    A --> F[sample_contracts/]

    B --> B1[legal-advisor/SKILL.md<br/>Analysis playbook]
    C --> C1[legal_env.py<br/>Atropos RL environment]
    D --> D1[demo_legal.py<br/>Full analysis + chat]
    F --> F1[EN + TR sample<br/>contracts]

    style B1 fill:#27ae60,color:#fff
    style C1 fill:#8e44ad,color:#fff
    style D1 fill:#2980b9,color:#fff
```

## Disclaimer

Hermes Legal Advisor provides contract analysis, not legal advice.
Always consult a qualified attorney before signing any contract.
