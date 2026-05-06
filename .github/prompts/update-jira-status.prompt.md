---
agent: release-pr
tools: ['edit', 'atlassian/*']
description: 'Update Jira ticket status to In Review and add completion comment.'
---

Update the Jira ticket to reflect SDLC completion.

Tasks:
- Update ticket status to "In Review" using `atlassian/*`.
- Add a comment summarizing:
  - PR link
  - Implementation summary
  - Test results (pass/fail counts)
  - All artifacts generated in `.stage/<JIRA-ID>/`
- Confirm status update to the user.
