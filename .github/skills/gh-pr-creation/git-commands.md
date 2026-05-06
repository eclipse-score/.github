# Git Command Reference

Essential git commands for PR creation workflow.

## Branch & Status

```bash
# Check current branch
git branch --show-current

# Check working directory status
git status

# Show changes summary
git diff --stat
```

## Commit History

```bash
# Show commits not in base branch
git log origin/<base-branch>..HEAD --oneline

# Fetch latest from remote
git fetch origin
```
