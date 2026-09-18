# Advanced: origin as a Hermes agent project

Hermes Legal Advisor started as an entry for NousResearch's "Show us what
Hermes Agent can do" hackathon. It didn't win, but the core analysis logic
was solid, so it has since been rebuilt as a standalone tool anyone can
install and use - independent of any specific AI agent framework.

The hackathon-specific pieces are kept in this repository under `extras/`
because they are still genuinely useful if you're working with the Hermes
agent framework or Nous Research's Atropos RL toolkit, but they are no
longer required to use Hermes Legal Advisor day to day.

## `extras/skills/legal-advisor/SKILL.md`

The original agent "skill" definition: an analysis playbook (ingest,
classify, extract, risk-score, compare, report, archive) written for
agent frameworks that support the Agent Skills convention (Claude Code,
Hermes agent, and similar). The rule library in
`src/hermes_legal/providers/offline_provider.py` is a direct, executable
implementation of this same playbook's red-flag list.

## `extras/atropos/legal_env.py`

An [Atropos](https://github.com/NousResearch/atropos) reinforcement
learning environment for training an agent to be a better contract
analyst. It defines five scenarios of varying difficulty and a reward
function with five weighted components:

| Component | Weight | Checks |
|---|---|---|
| Contract read | 15% | Did the agent actually load the contract? |
| Clauses scored | 30% | Did it score most/all clause categories? |
| Red flags found | 25% | Did it catch the red flags a human reviewer would? |
| Report saved | 20% | Did it produce a structured, saved report? |
| Risk accurate | 10% | Was the overall CRITICAL/HIGH/MEDIUM/LOW call correct? |

If you're training or fine-tuning an agent on contract review tasks, this
environment is a reasonable starting point - run its built-in smoke test
with:

```bash
python extras/atropos/legal_env.py
```

## Why this moved out of the main pitch

A hackathon README needs to explain "how it uses Hermes agent features."
A tool people actually install needs to explain "what problem this solves
for me, right now, for free." Both are true of the same codebase - this
document exists so the hackathon story isn't lost, while the main
`README.md` leads with what a new user actually needs.
