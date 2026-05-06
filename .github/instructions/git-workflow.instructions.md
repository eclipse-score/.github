---
applyTo: '**'
---

# Git Workflow

## Commit Message Format
```
<type>(<scope>): <description>

<optional body>

<optional footer: JIRA-ID>
```

### Types
`feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`, `style`

### Rules
- Use imperative mood: "add feature" not "added feature"
- Keep subject line under 72 characters
- Reference Jira ticket in footer when applicable
- One logical change per commit

## Branch Naming
Format: `<type>/<JIRA-ID>-<short-description>`

Examples:
- `feature/JIRA-123-add-login`
- `bugfix/JIRA-456-fix-null-pointer`
- `hotfix/JIRA-789-patch-auth`

## Pull Request Workflow
1. Analyze full commit history: `git diff <base-branch>...HEAD`
2. Draft comprehensive PR summary covering what changed and why
3. Include a test plan with verification steps
4. Push with `-u` flag if new branch
5. Request review from at least one peer

## Pre-Commit Checklist
- [ ] All tests pass locally
- [ ] No lint errors or warnings
- [ ] No `console.log` / `System.out.println` left in production code
- [ ] No TODO/FIXME without a linked ticket
- [ ] Commit message follows format above
- [ ] Branch is rebased on latest base branch

## Merge Strategy
- Squash merge for feature branches (clean history)
- Merge commit for release branches (preserve full history)
- Fast-forward for hotfixes when possible
