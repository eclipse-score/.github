---
agent: setup-repo
tools: ['execute', 'read', 'edit', 'github']
description: 'Clone an existing GitHub repository after confirming details with user.'
---

Clone an existing GitHub repository into the workspace.

Tasks:
- Ask the user for:
  - Repository name
  - Organization name (if multiple orgs available)
  - Branch to clone (if not default/main)
- Confirm collected details with the user.
- Validate repository exists and user has access permissions.
- Clone the specified branch using git CLI.
