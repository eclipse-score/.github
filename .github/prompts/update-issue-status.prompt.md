---
agent: release-pr
tools: ['edit', 'atlassian/*']
description: 'Update GitHub issue status to In Review and add completion comment.'
---

Update the GitHub issue to reflect SDLC completion.

Tasks:
- Update issue status to "In Review" using `atlassian/*`.
- Add a comment summarizing:
  - PR link
  - Implementation summary
  - Test results (pass/fail counts)
  - All artifacts generated in `.stage/<ISSUE-ID>/`
- Confirm status update to the user.
