---
agent: plan-tech-analysis
tools: ['read', 'edit', 'atlassian/*']
description: 'Push approved stories and tasks to GitHub Issues under the parent Epic. MCP fallback for manual creation.'
---

Create the approved stories as GitHub issues linked to the parent Epic.

## Tasks

### 1. Read Approved Stories
- Read all story files from `.stage/EPIC-XXX/stories/story-{prefix}-*.md`
- Extract for each: title, description, acceptance criteria, story points, dependencies

### 2. Create Story Issues in GitHub Issues
For each approved story:
- Use `atlassian/*` (createIssue) to create a Story with:
  - **Summary**: Story title
  - **Description**: What + Why + Acceptance Criteria (formatted)
  - **Issue Type**: Story
  - **Story Points**: from story file
- Use `atlassian/*` (createIssueLink) to link each Story to the parent Epic (EPIC-XXX)
- Record the created issue ID for each story

### 3. Update Story Files
- Update each `.stage/EPIC-XXX/stories/story-{prefix}-{N}.md` with the actual GitHub Story ID
- Present the created issues to the user:

| # | Story ID | GitHub Issue | Title | Points |
|---|----------|------------|-------|--------|
| 1 | {prefix}-1 | PROJ-101 | [title] | [pts] |
| 2 | {prefix}-2 | PROJ-102 | [title] | [pts] |

### 4. Add Epic Comment
- Use `atlassian/*` (addCommentToIssue) to add a comment on EPIC-XXX:
  > "Technical analysis complete. [N] stories created: [list of issue IDs]."

## MCP Fallback
If `atlassian/*` tools are unavailable or fail:

1. **Inform the user:**
   > "I'm unable to connect to GitHub Issues. No worries -- you can create the stories manually!"

2. **For each story, provide:**
   - Title
   - Description (formatted for GitHub Issues)
   - Story Points
   - Parent Epic ID to link to

3. **Ask the user to paste the created issue IDs:**
   > "Once you've created the stories in GitHub Issues, paste the issue IDs here so I can update the story files."

4. **Update story files** with manually provided IDs and continue.

## Rules
- Do NOT create issues without user approval of the stories
- Always link stories to the parent Epic
- If any issue creation fails, report the error and continue with remaining stories
- The pipeline never stops -- use MCP fallback if needed
