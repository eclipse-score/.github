---
agent: plan-requirements
tools: ['edit', 'atlassian/*']
description: 'Fetch a specific Jira ticket, assign developer if unassigned, and initialize SDLC context.'
---

Fetch the selected ticket and ensure a developer is assigned.

Tasks:
- Fetch Jira ticket details using `atlassian/*`.
- Extract title, description, and acceptance criteria.
- Create working folder: `.stage/<JIRA-ID>/`
- Create initial plan file: `.stage/<JIRA-ID>/plan.md`
- Check if a developer is assigned; if not, ask user to assign one.
- Update ticket with assigned developer.
- Update ticket status to "In Progress" using `atlassian/*`.
- Initialize SDLC context with extracted info.
