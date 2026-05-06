---
agent: code-implement
tools: ['vscode', 'execute', 'read', 'edit', 'search']
description: 'Review existing codebase to understand structure, dependencies, and impact areas.'
---

Thoroughly review the existing codebase before implementation.

Tasks:
- Navigate the codebase to understand overall structure and organization.
- Identify key modules, components, and their interactions.
- Review coding standards and conventions for consistency.
- Document dependencies, libraries, and frameworks used.
- Highlight areas impacted by the upcoming implementation plan.
- Save findings at: `.stage/<JIRA-ID>/codebaseReview.md`
- Prepare a summary report to guide the implementation phase.

## CRA / React Codebase Health Checks (required for React/TypeScript projects)

When reviewing a CRA or React/TypeScript codebase, include these checks in the review findings:
1. **ESLint config audit** — locate config, document rules likely to conflict, flag `DISABLE_ESLINT_PLUGIN=true` in `.env`
2. **Type safety audit** — scan `services/` and mocks for `null` returns without explicit return types
3. **i18n audit** — search for `returnObjects: true`, verify keys exist in ALL locale files
4. **Architecture patterns** — document whether pages follow single-file or multi-component pattern
5. **Route registration** — verify all imports in `AppRoutes.tsx` resolve to real, ESLint-clean files

> Full CRA safety rules are in `.github/instructions/react.instructions.md` (auto-applied for `.tsx`/`.ts` files).
