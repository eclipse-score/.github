---
agent: setup-repo
tools: ['execute', 'read', 'edit', 'github-enterprise/*']
description: 'Create a new GitHub repository following naming conventions and configure settings.'
---

Create a GitHub repository aligned with project requirements and naming conventions.

Tasks:
- Ask the user for:
  - Target organization (from accessible orgs)
  - Repository name and description
  - Visibility (public/private)
  - Required templates or initialization settings
- Create the repository using `github-enterprise/*`.
- Configure: default branch, branch protection rules, issue templates, security/compliance rules, and webhooks as required.
