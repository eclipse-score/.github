---
agent: plan-requirements
tools: ['edit', 'atlassian/*']
description: 'Create a new Jira ticket from provided details and return ticket ID and URL.'
---

Create a new Jira ticket based on user-provided details.

Tasks:
- Collect title, description, priority, and any relevant attachments from the user.
- Use `atlassian/*` to create a new ticket in the appropriate project and issue type.
- Ensure all mandatory fields are filled correctly.
- Retrieve and present the ticket ID and URL.
- Create working folder: `.stage/<JIRA-ID>/`
- Create initial plan file: `.stage/<JIRA-ID>/plan.md` with ticket details.
