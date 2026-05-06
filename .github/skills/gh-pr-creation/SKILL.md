---
name: gh-pr-creation
description: Use when creating a draft PR adhering to formatting standards, branch conventions, and issue links. Ensures clean, structured PR descriptions.
inference_examples:
  - "Create a PR for my changes"
  - "Open a pull request"
  - "Make a PR for this feature"
  - "Generate PR from current branch"
  - "Create pull request with AI description"
---

# GitHub PR Creation

**Git commands reference**: See [`git-commands.md`](./git-commands.md)

## 1. Core Rules

- **Draft First**: ALWAYS create as draft. Draft = work in progress.
- **Branch Naming**: MUST use kebab-case: `feature/description`, `fix/issue`, `refactor/component`.
- **PR Title**: MUST summarize changes clearly. Use conventional commit format for single-commit PRs.
- **PR Description**: MUST include Summary, Changes, Testing, Related Issues.
- **Issue Links**: MUST validate that referenced issues exist.
- **No Duplicates**: Check for existing PR and update instead of creating new one.

## 2. Workflow

### Step 1: Preparation

Analyze State of the Git Repository
- Clarify base branch (default: main)
- Check current branch (must not be main)
- Working directory status
- Read commit history compared to base branch (default: main)
- Identify related issues from commits, branch name and github metadata (labels, assignees, etc.)
    - Read issues and update with PR link or acceptance criteria status if needed
- Check for existing PRs with same branch or related issues
    - If existing PR found, update it instead of creating new one

### Step 2: Create or Update Draft PR

**Generate description** (analyze diff + commits) and create or update draft PR with:

```markdown
## Summary
[Concise one-paragraph overview]

## Changes
- **Component/File**: Specific change description

## Testing
- Unit tests: [status]
- Integration tests: [status]
- Manual testing: [what was tested]

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] CI passing

## Related Issues
Closes #123
Relates to #456
```

## Anti-Patterns

- Creating PR without description
- Mixing unrelated changes
- Pushing to main directly
- Vague titles: "Update code", "Fix bug"
- Missing issue links

### Relevant GitHub CLI Commands

**Multiline body pattern** (use when needed for PR/issue bodies or comments):

```bash
# Bash/Linux/Mac:
body=$(cat <<'EOF'
## Summary
Your markdown here
EOF
)
command --arg1 "value" --arg2 "$body"

# PowerShell/Windows:
$body = @"
## Summary
Your markdown here
"@
command --arg1 "value" --arg2 $body
```

**Commands:**

```bash
# Search for related issues
gh issue list --search "<keywords>" --json number,title,state,labels
gh issue list --label "<label>" --state open --json number,title

# Read issue details
gh issue view <number> --json state,title,body,labels,assignees

# Check existing PR
gh pr list --head <branch-name> --state open --json number,title,url

# Create draft PR
gh pr create --draft --title "Summary" --body "..." --base <base-branch>

# Update existing PR
gh pr edit <number> --title "..." --body "..."
```
