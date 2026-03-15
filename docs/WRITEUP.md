# Hermes Legal Advisor — Technical Writeup

## The Problem

Most people sign contracts without fully understanding what they contain.
Not because they don't care — because contracts are dense, jargon-heavy,
and deliberately written to be hard to read.

The result: people agree to 3-year worldwide non-competes, uncapped personal liability,
and IP assignments that cover work they do at midnight on their own laptop —
because they didn't catch it, or didn't know what it meant.

## The Solution

Hermes Legal Advisor reads contracts the way a thorough attorney would —
methodically, clause by clause, looking for the specific patterns that create risk.

It doesn't just summarize. It scores. It flags. It compares against every contract
you've analyzed before, so it can tell you when a counter-party is getting
progressively worse in their terms across engagements.

## Analysis Pipeline

INGEST: Load the full contract text, identify language, count sections.

CLASSIFY: Determine contract type — Freelance, Employment, NDA, SaaS, Partnership, etc.

SCORE: Evaluate 9 clause categories on a 1-10 risk scale:
Termination, Liability, IP Ownership, Non-Compete, Confidentiality,
Payment Terms, Governing Law, Auto-Renewal, Dispute Resolution.

COMPARE: Search memory for prior contracts from the same counter-party.
Flag if terms have gotten worse. Surface recurring patterns.

ALERT: If overall risk is CRITICAL or HIGH, trigger an immediate alert via Gateway.
Extensible to email, Slack, or any notification channel.

REPORT: Save a structured Markdown report with executive summary, clause-by-clause
findings, extracted key terms, and prioritized recommendations.

ARCHIVE: Store contract metadata in memory — type, parties, risk level, hash.
The next analysis of the same party benefits from this history.

## Atropos RL Integration

The reward function trains Hermes to become a sharper analyst over time:

- Contract Read (15%): Did it actually load and process the document?
- Clauses Scored (30%): Did it score all 9 clause categories?
- Red Flags Found (25%): Did it identify the expected problematic terms?
- Report Saved (20%): Did it produce a structured, persistent report?
- Risk Accurate (10%): Did it correctly assess the overall risk level?

Five training scenarios span the range from balanced NDAs to critically
unfavorable freelance contracts, ensuring Hermes learns to calibrate
risk across the full spectrum.

## Why This Matters

Most AI legal tools summarize. Hermes Legal Advisor analyzes.

Summarizing tells you what a contract says.
Analyzing tells you what a contract means for you — and what to do about it.

Combined with Memory, every analysis makes the next one better.
A counter-party that consistently includes unfavorable terms gets flagged earlier.
Patterns that emerge across dozens of contracts become visible.

That's not a tool. That's institutional knowledge.
