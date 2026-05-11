---
agent: plan-community-roadmap
tools: ['read', 'edit', 'search', 'github']
description: 'Collect related issues and discussions to establish roadmap context.'
---

Collect and summarize the context for a roadmap initiative.

## Tasks
- Ask the user for candidate issue numbers, labels, milestones, or discussion links.
- Fetch related issues and summarize: title, status, owner, dependencies, and blockers.
- Capture discussion signals from issue comments/PR feedback when available.
- Write issue context summary to `.stage/ROADMAP-XXX/issue-summary.md`.

## Rules
- Prefer existing issue evidence over assumptions.
- Mark unknowns explicitly and carry them to the next step.
