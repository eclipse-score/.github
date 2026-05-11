---
agent: plan-tech-analysis
tools: ['read', 'edit', 'github']
description: 'Push approved tasks to GitHub Issues under the parent initiative issue. MCP fallback for manual creation.'
---

Create the approved tasks as GitHub issues linked to the parent initiative issue.

## Tasks

### 1. Read Approved Stories
- Read all task files from `.stage/<INITIATIVE-ID>/tasks/task-{prefix}-*.md`
- Extract for each: title, description, acceptance criteria, size, dependencies

### 2. Create Task Issues in GitHub
For each approved task:
- Create a GitHub Issue with Type: **Task**
  - **Summary**: Task title
  - **Description**: What + Why + Acceptance Criteria (formatted)
  - **Size**: from task file (S/M/L/XL)
- Link each task to the parent initiative issue (`<INITIATIVE-ID>`) using GitHub issue dependencies
- Record the created issue number for each task

### 3. Update Task Files
- Update each `.stage/<INITIATIVE-ID>/tasks/task-{prefix}-{N}.md` with the actual GitHub issue number
- Present the created issues to the user:

| # | Task ID | GitHub Issue | Title | Size |
|---|----------|------------|-------|--------|
| 1 | {prefix}-1 | #101 | [title] | [pts] |
| 2 | {prefix}-2 | #102 | [title] | [pts] |

### 4. Add Parent Issue Comment
- Add a comment on the parent initiative issue (`<INITIATIVE-ID>`):
  > "Technical analysis complete. [N] tasks created: [list of issue numbers]."

## MCP Fallback
If GitHub API is unavailable or user prefers manual creation:

1. **Inform the user:**
   > "I can help you format the task data for manual GitHub issue creation."

2. **For each task, provide:**
   - Title
   - Description (formatted for GitHub Issues)
   - Size (S/M/L/XL per SCORE standards)
   - Parent initiative issue ID to link to

3. **Ask the user to paste the created issue numbers:**
   > "Once you've created the tasks in GitHub, paste the issue numbers (#NNN) here so I can update the task files."

4. **Update story files** with manually provided IDs and continue.

## Rules
- Do NOT create issues without user approval of the tasks
- Always link tasks to the parent initiative issue
- If any issue creation fails, report the error and continue with remaining tasks
- The pipeline never stops -- use MCP fallback if needed
