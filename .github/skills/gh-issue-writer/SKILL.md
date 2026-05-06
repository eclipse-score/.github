---
name: gh-issue-writer
description: Use when creating GitHub issues via GitHub CLI. Validates issue quality and enforces Goal/Acceptance Criteria/Description structure.
inference_examples:
  - "Create a GitHub issue for this feature"
  - "Write an issue for implementing authentication"
  - "Generate a story for the kanban board"
  - "Make a GitHub issue for this bug"
  - "Create an issue with labels and assignees"
---

# GitHub Issue Writer

## 1. Core Rules

- **Goal**: MUST state what and why. Outcome must be measurable.
- **Acceptance Criteria**: MUST be checklist format (`- [ ]`). Each criterion must be specific and testable.
- **Description**: OPTIONAL. Add only when Goal/AC insufficient for clarity.
- **Title**: MUST be clear and actionable. Avoid vague terms like "Fix bug" or "Update code".
- **Validation**: MUST validate quality before creating. Ask clarifying questions ONE at a time if input is vague.
- **No Duplicates**: MUST check for existing issues before creating.

## 2. Workflow

### Step 1: Gather and Clarify

- If input is vague, ask ONE clarifying question at a time
  - Focus on clarifying Goal and Acceptance Criteria first
  - As a last priority, clarify labels, assignees, and milestones
- After 2–3 exchanges, produce a draft even if incomplete
- On subsequent iterations, show ONLY changed sections
- Print the entire issue only on first draft, final creation, or when user requests it

### Step 2: Validate Quality

BEFORE creating, check:
- **Goal completeness**: Contains what, why, and measurable outcome
- **AC specificity**: Each criterion is testable; no generic items like "adheres to code standards" or "add tests"
- **Clarity**: No unexplained jargon or ambiguous requirements
- **Metadata**: Labels, assignees, and milestone provided if relevant
- **No duplicates**: Search for similar issues

If validation fails or duplicates found → ask ONE clarifying question.

### Step 3: Create and Confirm Issue

- Create issue with validated title, body (adhere to the template)
- Add labels, assignees and milestones if provided
- Confirm created issue content matches expectations
- Share issue URL and ID with user

Template for issue body:
```markdown
## Goal
{goal_statement — what, why, measurable outcome}

## Acceptance Criteria
- [ ] {specific, testable criterion}
- [ ] {specific, testable criterion}

## Description
{optional — add only if Goal/AC are insufficient}
```

### Anti-Patterns

- Generic AC like "add tests", "follows code standards" — focus on issue-specific criteria
- Creating an issue without validation — quality gate is mandatory
- Showing full issue on every iteration — wastes context
- Multiple clarifying questions at once — overwhelming for user
- Vague titles like "Fix bug" or "Update thing"

### Relevant GitHub CLI Commands

**Multiline body pattern** (use when needed):

```bash
# Bash/Linux/Mac:
body=$(cat <<'EOF'
## Goal
Your markdown here
EOF
)
command --arg1 "value" --arg2 "$body"

# PowerShell/Windows:
$body = @"
## Goal
Your markdown here
"@
command --arg1 "value" --arg2 $body
```

**Commands:**

```bash
# Search for existing issues
gh issue list --search "<title keywords>" --state open

# List available labels
gh label list --json name --jq '.[].name'

# List repository collaborators (potential assignees)
gh api repos/{owner}/{repo}/collaborators --jq '.[].login'

# Create issue
gh issue create --title "..." --body "..." --label "..." --assignee "..."
```
