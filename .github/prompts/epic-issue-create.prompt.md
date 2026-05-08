---
agent: plan-epic-creation
tools: ['read', 'edit', 'atlassian/*']
description: 'Create the Epic in GitHub Issues via MCP. Check for duplicates. Rename EPIC-DRAFT to EPIC-XXX.'
---

Create the approved Epic as a GitHub issue and rename the staging folder.

## Tasks

### 1. Check for Duplicates
- Use `atlassian/*` to search for existing Epics with similar title or keywords
- If a potential duplicate is found, present it to the user:
  > "I found an existing Epic that looks similar: [EPIC-ID] — [Title]. Is this a duplicate, or should I create a new one?"
- If user confirms duplicate → stop, use the existing Epic ID
- If no duplicate or user says create → proceed

### 2. Create Epic in GitHub Issues
- Read `.stage/EPIC-DRAFT/epic.md` for the Epic content
- Use `atlassian/*` (createIssue) to create an Epic with:
  - **Summary**: Epic title from `epic.md`
  - **Description**: Full Epic content (Definition + Business Justification + Scope)
  - **Issue Type**: Epic
  - **Priority**: Derive from risk assessment in `epic.md`
- Retrieve the created Epic ID (e.g., `EPIC-123`)
- Present the issue ID and URL to the user

### 3. Rename Staging Folder
- Rename `.stage/EPIC-DRAFT/` → `.stage/EPIC-XXX/` (using actual GitHub issue ID)
- Update all file references inside the folder to use the new Epic ID

### 4. Update Artifacts
- Update `functional-spec.md`: replace `EPIC-DRAFT` with actual Epic ID
- Update `epic.md`: replace `EPIC-DRAFT` with actual Epic ID
- Confirm to user: "Epic EPIC-XXX created and all artifacts updated."

## MCP Fallback
If `atlassian/*` tools are unavailable or fail:

1. **Inform the user:**
   > "I'm unable to connect to GitHub Issues. No worries — you can create the Epic manually!"

2. **Provide manual creation instructions:**
   - Title: [from epic.md]
   - Description: [formatted content]
   - Type: Epic
   - Priority: [derived]

3. **Ask the user to paste the Epic ID** after manual creation:
   > "Once you've created the Epic in GitHub Issues, paste the Epic ID here (e.g., EPIC-123)."

4. **Proceed with rename** using the manually provided ID.

## Rules
- Do NOT create the issue without user approval of the Epic document
- Always check for duplicates before creating
- Always rename the staging folder after creation
