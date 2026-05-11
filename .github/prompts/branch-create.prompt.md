---
agent: code-design
tools: ['read', 'edit', 'github']
description: 'Create a GitHub branch based on GitHub issue type following naming conventions.'
---

Create a branch based on the GitHub issue type and details.

Tasks:
- Analyze the issue to determine type (feature, bugfix, hotfix, chore).
- Select the appropriate prefix:
  - Feature: `feature/`
  - Bugfix: `bugfix/`
  - Hotfix: `hotfix/`
  - Chore: `chore/`
- Construct branch name: `<prefix><ISSUE-ID>-<short-description>` (lowercase, hyphen-separated).
- Create the branch in the GitHub repository.
- Save branch details to: `.stage/<ISSUE-ID>/plan.md`
