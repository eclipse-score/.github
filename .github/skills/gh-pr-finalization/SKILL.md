---
name: gh-pr-finalization
description: Use when refining a PR through review cycles, addressing feedback, and preparing for merge. Detects current PR phase and continues accordingly.
inference_examples:
  - "Mark PR ready for review"
  - "Address review comments on my PR"
  - "Finalize my pull request"
  - "What do reviewers say about PR?"
  - "Re-request review after changes"
  - "Merge this PR"
---

# GitHub PR Finalization

**Git commands reference**: See [`git-commands.md`](./git-commands.md)

## 1. Core Rules

- ALWAYS detect current phase first (draft/ready/approved)
- Copilot review BEFORE human reviewers
- EVERY review comment MUST be addressed (fix or explain)
- Keep branch up-to-date with base throughout process
- Ask user before rebasing/force-pushing
- Prefer UI merge over CLI merge
- NEVER mark ready without CI green and no TODO/FIXME
- Resolve threads only after code fixes, leave open for replies

## 2. Workflow

### Phase Detection (ALWAYS RUN FIRST)

This skill may be invoked at any stage. Detect current phase:

**Phase indicators**:
- Draft + no reviews → Phase 1 (Pre-Review Validation)
- Ready + reviews pending/in-progress → Phase 2 (Review Loop)
- Ready + approved + all threads resolved/addressed → Phase 3 (Merge Prep)

### Phase 1: Pre-Review Validation

First, validate PR adheres to `gh-pr-creation` standards. Use that skill to check.
Fix any issues before continuing.

**Then, additional checks:**
- Ensure branch up-to-date with base
- Confirm CI is green
- Scan diff for TODO/FIXME

If any check fails → inform user and pause.

If all checks pass → Mark PR as ready and proceed to Phase 2.

### Phase 2: Review Loop

#### Step 1: Request Reviews

- Request Copilot review first
- After Copilot feedback addressed: request human review (use codeowners or ask user for reviewers)

#### Step 2: Address Feedback & Iterate

- Fetch all review comments (inline, top-level, general)
  - If no comments / review, inform user and wait for reviews
- Categorize by severity (security > bugs > logic > style > nits)
- For each comment:
  - **Fix it**: Make code change, commit, push
  - **Explain**: Reply with reasoning (by design, out of scope)
  - **Ask user**: If unclear, present comment and ask
- Resolve threads where code fix was applied (leave open for explanations)
- Re-request reviews after changes

**Loop**: Repeat Step 2 until all reviews approved and all threads resolved/addressed.

### Phase 3: Final Validation & Merge Prep

**Pre-merge checklist**:
- All conversations resolved
- All required approvals received
- Branch up-to-date with base
- CI green

If ANY condition fails → inform user and return to Phase 2.

If ALL pass:
```
✅ PR is ready to merge!

Review one final time and merge via GitHub UI:
https://github.com/{owner}/{repo}/pull/{number}
```

**If user explicitly says "merge this PR"**:
- Ask: _"Which merge strategy? (merge/squash/rebase)"_
- Execute merge via CLI

### Anti-Patterns

- Marking ready without CI green
- Requesting human reviewers before Copilot review is completed and resolved
- Ignoring review comments
- Force-pushing without user consent
- Merging with unresolved conversations
- Auto-resolving threads without fixes

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
# Check PR status and phase
gh pr view <number> --json state,isDraft,reviewDecision,statusCheckRollup
gh pr view <number> --json reviews
gh pr checks <number> --json state,conclusion

# Scan for TODO/FIXME
gh pr diff <number> | grep -E "TODO|FIXME"

# Mark ready and manage reviewers
gh pr ready <number>
gh pr edit <number> --add-reviewer "github-copilot[bot]"
gh pr edit <number> --add-reviewer username1,username2

# Fetch review comments
gh api repos/{owner}/{repo}/pulls/{number}/comments \
  --jq '.[] | "[\(.path):\(.line)] @\(.user.login): \(.body)\n---"'
gh pr view <number> --json reviews \
  --jq '.reviews[] | "[\(.state)] @\(.author.login): \(.body)"'
gh pr view <number> --json comments \
  --jq '.comments[] | "@\(.author.login): \(.body)"'

# Reply and manage threads
gh pr comment <number> --body "Addressed in commit abc123"

# Get review thread IDs (GraphQL)
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            id
            isResolved
            comments(first: 1) { nodes { body path } }
          }
        }
      }
    }
  }
' -f owner={owner} -f repo={repo} -F pr={number}

# Resolve thread (GraphQL)
gh api graphql -f query='
  mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread { isResolved }
    }
  }
' -f threadId={node_id}

# Final validation
gh pr view <number> --json reviewDecision,statusCheckRollup,mergeable

# Merge
gh pr merge <number> --merge   # or --squash or --rebase
```
