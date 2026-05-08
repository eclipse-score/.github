---
agent: plan-requirements
tools: ['edit', 'atlassian/*']
description: 'Fetch a specific GitHub issue, assign developer if unassigned, and initialize SDLC context.'
---

Fetch the selected issue and ensure a developer is assigned.

Tasks:
- Fetch GitHub issue details using `atlassian/*`.
- Extract title, description, and acceptance criteria.
- Create working folder: `.stage/<ISSUE-ID>/`
- Create initial plan file: `.stage/<ISSUE-ID>/plan.md`
- Check if a developer is assigned; if not, ask user to assign one.
- Update issue with assigned developer.
- Update issue status to "In Progress" using `atlassian/*`.
- Initialize SDLC context with extracted info.
