---
agent: plan-tech-analysis
tools: ['read', 'github']
description: 'Read roadmap/initiative context from GitHub Issues or .stage/ artifacts and summarize requirements for the Tech Lead.'
---

Fetch and summarize roadmap/initiative context for technical analysis.

## Tasks

### 1. Locate Initiative Artifacts
- Check if `.stage/<INITIATIVE-ID>/` folder exists (from `@plan-community-roadmap` handoff)
- If yes: prefer reading `.stage/<INITIATIVE-ID>/roadmap.md` and `.stage/<INITIATIVE-ID>/issue-summary.md`
- If no: ask the user for the initiative ID or parent issue ID, then try:
    - Issue tracker MCP or `gh issue view` CLI to fetch initiative details from GitHub Issues
  - If MCP unavailable: ask user to paste the summary

### 2. Summarize for Tech Lead
- Extract from initiative artifacts:
  - Business goal and value
  - Functional requirements list
  - Acceptance criteria
  - Success metrics
  - Scope boundaries (in scope / out of scope)
  - Dependencies and constraints
- Hold this summary internally for use in subsequent steps
- Do NOT save a separate file -- this is an internal working summary

### 3. Confirm with User
- Present a brief summary: "I've read initiative <INITIATIVE-ID>. Here's what I understand: [2-3 sentence summary]. Ready to analyze a repository?"

## Rules
- If initiative artifacts are missing AND GitHub Issues is unavailable, do NOT proceed without initiative context
- Do NOT modify roadmap artifacts produced by `@plan-community-roadmap`
