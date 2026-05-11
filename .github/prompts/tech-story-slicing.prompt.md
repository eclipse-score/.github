---
agent: plan-tech-analysis
tools: ['read', 'edit', 'search']
description: 'Vertical slicing rules. Generate complete stories + test outlines. User review gate.'
---

Slice the technical analysis into vertically sliced user stories with test scenario outlines.

## Tasks

### 1. Read Inputs
- Read `.stage/<INITIATIVE-ID>/tech-analysis/{repo-name}-analysis.md` (approved by user)
- Read `.github/skills/tech-analysis/assets/task-template.md`
- Read `.github/skills/tech-analysis/assets/test-scenario-template.md`
- Use initiative context for business value references

### 2. Determine Story Prefix
- Derive a short prefix from the repo name (e.g., `auth-svc` → `AUTH`, `web-app` → `WEB`)
- Use this prefix for all story files: `task-{prefix}-{N}.md`

### 3. Slice into Vertical Stories
Apply vertical slicing rules:
- Each task MUST deliver a **complete vertical slice** within one service/module
- Each task MUST be **independently deployable and testable**
- Each task SHOULD be completable within **one sprint** (≤ 8 size)
- If a task exceeds 8 size → split further
- No "backend-only" or "frontend-only" tasks unless the repo is single-concern

For each task, fill the task template with:
- **What**: clear description of the deliverable
- **Why**: link to business value from initiative context
- **Acceptance Criteria**: Given/When/Then format, covering happy path + error cases
- **Files Affected**: specific file paths from codebase analysis
- **Size**: estimate based on complexity and scope
- **Dependencies**: other stories, external teams, or "None"
- **Out of Scope**: what this story explicitly does NOT include

### 4. Generate Test Scenario Outlines
- For each story, create lightweight test scenarios (3-5 per story)
- Use the test scenario template: Given/When/Then bullets only
- Cover: happy path, error handling, edge cases
- Do NOT write actual test code -- that is `@test-qa`'s job

### 5. Save Stories and Test Outlines
- Save each task to: `.stage/<INITIATIVE-ID>/tasks/task-{prefix}-{N}.md`
- Save test outlines to: `.stage/<INITIATIVE-ID>/tasks/tests/{prefix}-test-scenarios.md`

### 6. Present Story Summary and Review Gate
Present a summary table to the user:

| # | Task ID | Title | Points | Dependencies |
|---|----------|-------|--------|-------------|
| 1 | {prefix}-1 | [title] | [pts] | [deps] |
| 2 | {prefix}-2 | [title] | [pts] | [deps] |

Ask: "Review the tasks above. You can:
- **Split** a task (tell me which one and why)
- **Merge** two tasks (tell me which ones)
- **Modify** a task (tell me what to change)
- **Proceed** to create these in GitHub Issues"

## Rules
- Do NOT proceed to GitHub Issues creation until user approves the stories
- If user requests split/merge/modify, update files and re-present
- Each story must be self-contained -- a developer should understand it without reading other stories
- Story points must be realistic: 1 (trivial), 2 (small), 3 (medium), 5 (large), 8 (very large)
