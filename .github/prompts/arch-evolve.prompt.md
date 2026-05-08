---
agent: code-architect
tools: ['vscode', 'execute', 'read', 'edit', 'search', 'github-enterprise/*', 'atlassian/*', 'todo']
description: 'Analyze codebase for architectural drift and health assessment.'
---

Analyze the codebase against documented decisions to find drift and improvement opportunities.

Prerequisites:
- `.stage/docs/architecture.md` must exist. If not, inform the user to run `/arch init` first.

Tasks:
- Read `.stage/docs/architecture.md` and all accepted DRs
- Scan the codebase structure (directory layout, import patterns, naming conventions)
- Compare actual patterns against documented decisions and boundaries
- Identify:
  - **Drift** — code that has diverged from documented decisions
  - **Inconsistencies** — parts of the codebase that follow different patterns
  - **Missing decisions** — patterns in the code that aren't captured in any DR
  - **Stale decisions** — DRs that no longer reflect reality

Produce an Architecture Health Report:

```markdown
## Architecture Health Report

### Drift
- <description, with file references>

### Inconsistencies
- <description, with examples>

### Suggested New Decisions
- <pattern that should be formalized as a DR>

### Potentially Stale DRs
- DR-NNN: <why it may be outdated>

### Health Assessment
| Area | Findings |
|------|----------|
| Strengths | ... |
| Weaknesses | ... |
| Quick wins | ... |
| Medium effort | ... |
| Major refactors | ... |
```

- Offer to create new DRs (via `dr-expert` skill) for any findings
- Ground all suggestions in the team's own decisions, not generic best practices
- Add GitHub Issues comment: "Architecture evolution analysis completed"
