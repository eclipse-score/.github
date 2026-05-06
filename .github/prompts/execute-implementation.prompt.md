---
agent: code-implement
tools: ['vscode', 'execute', 'read', 'edit', 'search', 'github-enterprise/*']
description: 'Execute the implementation plan -- write code, test, and document changes.'
---

Execute the tasks outlined in the implementation plan.

Tasks:
- Review `.stage/<JIRA-ID>/plan.md` for scope and task details.
- Set up development environment for coding and testing.
- Implement code according to plan tasks and milestones.
- Conduct initial testing of implemented features.
- Document challenges or deviations and how they were resolved.
- Prepare a summary report at: `.stage/<JIRA-ID>/implementationReport.md`
- Ensure all code changes are pushed to the working branch.

## CRA / React Pre-Flight Checklist (run BEFORE marking implementation complete)

For every new or modified `.ts`/`.tsx` file in a React CRA project, verify:
1. **TypeScript** — No bare `null` returns without explicit return types on service/mock functions
2. **ESLint** — Run `npx eslint --max-warnings=0` on each new file before integration
3. **i18n** — No `returnObjects: true` for unverified translation keys
4. **Single-file first** — New pages as one self-contained file before sub-component extraction
5. **Route registration** — Add route only after component exists and is ESLint-clean

> Full CRA safety rules are in `.github/instructions/react.instructions.md` (auto-applied for `.tsx`/`.ts` files).
