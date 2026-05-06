---
agent: plan-tech-analysis
tools: ['read', 'search']
description: 'Ask for repo local path. If not cloned, suggest @setup-repo.'
---

Establish the repository path for technical analysis.

## Tasks

### 1. Ask for Repository Path
- Ask: "Which repository do you want to analyze for this Epic? Please provide the local path."
- If user provides a path: verify it exists by attempting to read a file (e.g., README.md, package.json, pom.xml)
- If path is valid: confirm and proceed

### 2. Handle Missing Repository
If the repo is not cloned locally:
- Suggest: "It looks like the repository isn't available locally. You can use **@setup-repo** to clone it, then come back."
- Wait for user to provide a valid path before proceeding
- Do NOT attempt to clone the repository yourself

### 3. Confirm Repository
- Present: "I'll analyze the repository at: `[path]`. Proceeding to codebase analysis."

## Rules
- A valid local repo path is REQUIRED -- do not proceed without one
- Do NOT guess or assume repository paths
- Accept any repo structure (monorepo, microservice, library, etc.)
