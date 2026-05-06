# Git Command Reference

Essential git commands for PR finalization workflow.

## Remote Sync

```bash
# Fetch latest from remote
git fetch origin

# Rebase onto base branch
git rebase origin/<base-branch>

# Continue after resolving conflicts
git rebase --continue

# Abort rebase
git rebase --abort

# Force push after rebase (use with caution)
git push --force-with-lease
```

## Branch Status

```bash
# Check current branch
git branch --show-current

# Show commits not in base branch
git log origin/<base-branch>..HEAD --oneline
```
