---
agent: code-design
tools: ['read', 'edit', 'github-enterprise/*']
description: 'Create a GitHub branch based on Jira ticket type following naming conventions.'
---

Create a branch based on the Jira ticket type and details.

Tasks:
- Analyze the ticket to determine type (feature, bugfix, hotfix, chore).
- Select the appropriate prefix:
  - Feature: `feature/`
  - Bugfix: `bugfix/`
  - Hotfix: `hotfix/`
  - Chore: `chore/`
- Construct branch name: `<prefix><JIRA-ID>-<short-description>` (lowercase, hyphen-separated).
- Create the branch in the GitHub repository.
- Save branch details to: `.stage/<JIRA-ID>/plan.md`
