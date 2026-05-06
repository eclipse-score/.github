---
agent: code-architect
tools: ['vscode', 'execute', 'read', 'edit', 'search', 'github-enterprise/*', 'atlassian/*', 'todo']
description: 'Record a new architectural decision with tradeoff analysis.'
---

Record a new architectural decision.

Prerequisites:
- `.stage/docs/architecture.md` must exist. If not, inform the user to run `/arch init` first.

Tasks:
- Read `.stage/docs/architecture.md` and list existing ADRs in `docs/adr/`
- Ask the user interactively:
  1. "What decision are you recording?"
  2. "What context led to this decision?"
  3. "What alternatives were considered?"
- Build a tradeoff table for each alternative (including chosen option):

| Option | Pros | Cons | Suitability |
|--------|------|------|-------------|
| A: [name] | ... | ... | When to pick this |
| B: [name] | ... | ... | When to pick this |
| C: Do nothing | ... | ... | When this is acceptable |

- Ask: "What are the consequences or trade-offs of the chosen option?"
- Determine the next ADR number by scanning `docs/adr/`
- Invoke the `adr-expert` skill to create `docs/adr/ADR-NNNN-<slug>.md`
- Update `.stage/docs/architecture.md` if the decision affects any key or boundary:
  - Changed key → update value
  - New category → add key
  - New boundary → append to boundaries
  - Superseded ADR → update old ADR status to "Superseded by ADR-NNNN"
- Present changes for user review before writing
- Add Jira comment: "Architecture decision recorded: ADR-NNNN"
