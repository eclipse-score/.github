---
agent: plan-requirements
tools: ['edit', 'atlassian/*']
description: 'Create a new GitHub issue from provided details and return issue ID and URL.'
---

Create a new GitHub issue based on user-provided details.

Tasks:
- Collect title, description, priority, and any relevant attachments from the user.
- Use `atlassian/*` to create a new issue in the appropriate project and issue type.
- Ensure all mandatory fields are filled correctly.
- Retrieve and present the issue ID and URL.
- Create working folder: `.stage/<ISSUE-ID>/`
- Create initial plan file: `.stage/<ISSUE-ID>/plan.md` with issue details.
