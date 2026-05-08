---
agent: plan-tech-analysis
tools: ['read', 'atlassian/*']
description: 'Read Epic from GitHub Issues or .stage/ artifacts and summarize business requirements for the Tech Lead.'
---

Fetch and summarize the Epic context for technical analysis.

## Tasks

### 1. Locate Epic Artifacts
- Check if `.stage/EPIC-XXX/` folder exists (from `@plan-epic-creation` handoff)
- If yes: read `.stage/EPIC-XXX/functional-spec.md` and `.stage/EPIC-XXX/epic.md`
- If no: ask the user for the Epic ID, then try:
  - `atlassian/*` (getIssue) to fetch Epic details from GitHub Issues
  - If MCP unavailable: ask user to paste the Epic summary

### 2. Summarize for Tech Lead
- Extract from Epic artifacts:
  - Business goal and value
  - Functional requirements list
  - Acceptance criteria
  - Success metrics
  - Scope boundaries (in scope / out of scope)
  - Dependencies and constraints
- Hold this summary internally for use in subsequent steps
- Do NOT save a separate file -- this is an internal working summary

### 3. Confirm with User
- Present a brief summary: "I've read Epic EPIC-XXX. Here's what I understand: [2-3 sentence summary]. Ready to analyze a repository?"

## Rules
- If Epic artifacts are missing AND GitHub Issues is unavailable, do NOT proceed without Epic context
- Do NOT modify Epic artifacts -- they belong to `@plan-epic-creation`
