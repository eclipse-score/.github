---
agent: release-pr
tools: ['execute', 'read', 'edit', 'github']
description: 'Create a Pull Request for the development branch changes.'
---

Create a Pull Request for the completed work.

Tasks:
- Push local changes to the remote branch using git CLI or GitHub MCP.
- Ask the user which target branch to merge into.
- Create a Pull Request with:
  - Descriptive title referencing the ISSUE ID
  - Summary of changes from `.stage/<ISSUE-ID>/implementationReport.md`
  - Test results summary from `.stage/<ISSUE-ID>/testResults.md`
  - Link to the GitHub issue
- Present the PR URL to the user.
