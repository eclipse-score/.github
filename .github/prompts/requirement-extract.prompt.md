---
agent: plan-requirements
tools: ['vscode', 'execute', 'read', 'edit', 'search', 'web', 'atlassian/*', 'agent', 'todo']
description: 'Extract clear, testable requirements from GitHub issue details.'
---

Generate clear and testable software requirements from the GitHub issue.

Tasks:
- Analyze issue title, description, and acceptance criteria.
- Extract key requirements ensuring they are SMART (Specific, Measurable, Achievable, Relevant, Time-bound).
- Rewrite requirements in clear, unambiguous language.
- Identify edge cases and special conditions.
- Flag missing information or ambiguities needing clarification.
- Finalize scope to ensure requirements are development-ready.
- Append refined requirements to: `.stage/<ISSUE-ID>/plan.md`
