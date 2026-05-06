---
agent: plan-tech-analysis
tools: ['read', 'edit', 'search']
description: 'Vertical slicing rules. Generate complete stories + test outlines. User review gate.'
---

Slice the technical analysis into vertically sliced user stories with test scenario outlines.

## Tasks

### 1. Read Inputs
- Read `.stage/EPIC-XXX/tech-analysis/{repo-name}-analysis.md` (approved by user)
- Read `.github/skills/tech-analysis/assets/story-template.md`
- Read `.github/skills/tech-analysis/assets/test-scenario-template.md`
- Use Epic context for business value references

### 2. Determine Story Prefix
- Derive a short prefix from the repo name (e.g., `auth-svc` → `AUTH`, `web-app` → `WEB`)
- Use this prefix for all story files: `story-{prefix}-{N}.md`

### 3. Slice into Vertical Stories
Apply vertical slicing rules:
- Each story MUST deliver a **complete vertical slice** within one service/module
- Each story MUST be **independently deployable and testable**
- Each story SHOULD be completable within **one sprint** (≤ 8 story points)
- If a story exceeds 8 points → split further
- No "backend-only" or "frontend-only" stories unless the repo is single-concern

For each story, fill the story template with:
- **What**: clear description of the deliverable
- **Why**: link to business value from Epic
- **Acceptance Criteria**: Given/When/Then format, covering happy path + error cases
- **Files Affected**: specific file paths from codebase analysis
- **Story Points**: estimate based on complexity and scope
- **Dependencies**: other stories, external teams, or "None"
- **Out of Scope**: what this story explicitly does NOT include

### 4. Generate Test Scenario Outlines
- For each story, create lightweight test scenarios (3-5 per story)
- Use the test scenario template: Given/When/Then bullets only
- Cover: happy path, error handling, edge cases
- Do NOT write actual test code -- that is `@test-qa`'s job

### 5. Save Stories and Test Outlines
- Save each story to: `.stage/EPIC-XXX/stories/story-{prefix}-{N}.md`
- Save test outlines to: `.stage/EPIC-XXX/stories/tests/{prefix}-test-scenarios.md`

### 6. Present Story Summary and Review Gate
Present a summary table to the user:

| # | Story ID | Title | Points | Dependencies |
|---|----------|-------|--------|-------------|
| 1 | {prefix}-1 | [title] | [pts] | [deps] |
| 2 | {prefix}-2 | [title] | [pts] | [deps] |

Ask: "Review the stories above. You can:
- **Split** a story (tell me which one and why)
- **Merge** two stories (tell me which ones)
- **Modify** a story (tell me what to change)
- **Proceed** to create these in Jira"

## Rules
- Do NOT proceed to Jira creation until user approves the stories
- If user requests split/merge/modify, update files and re-present
- Each story must be self-contained -- a developer should understand it without reading other stories
- Story points must be realistic: 1 (trivial), 2 (small), 3 (medium), 5 (large), 8 (very large)
