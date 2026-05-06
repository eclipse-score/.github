---
name: gh-status-updates
description: Check GitHub status — assigned issues/PRs, pending reviews, unassigned issues, and recent activity. Defaults to current repo; supports org-wide queries.
inference_examples:
  - "What's my GitHub status?"
  - "Any new issues assigned to me?"
  - "Show me PRs I need to review"
  - "What happened in the last 3 days?"
  - "Any unassigned issues?"
  - "Show me all open PRs in the org"
---

# GitHub Status Updates

## 1. Core Rules

- **Default scope**: Current repository only.
- **Org-wide scope**: Only when user explicitly says "org", "organization", or names the org.
- **Freshness**: Default "recent activity" window is 7 days (user can override).
- **Identify user**: Get current user's GitHub username before querying.
- **Relative timestamps**: Show "2d ago", "1w ago" instead of raw dates.
- **Skip empty sections**: Only show categories with results.

## 2. Workflow

### Step 1: Identify Current User

Get the user's GitHub username for personalized queries.

### Step 2: Determine Scope

- **Current repo** (default): Infer from `gh repo view`
- **Org-wide**: Only if user explicitly requests it

### Step 3: Run Relevant Queries

For a full status update ("What's my GitHub status?"), query:
1. Issues assigned to me
2. PRs authored by me
3. PRs pending my review
4. Unassigned issues (if user is maintainer/PO)
5. Recent activity (last 7 days)

Skip steps based on user's specific request (e.g., "show me PRs I need to review" → only step 3).

### Step 4: Format and Present Results

Present as clear summary grouped by category:

```
## GitHub Status for @username

### Assigned to me (3 issues, 1 PR)
- #42 Tool: Skill and Agent Installation (issue, updated 2d ago)
- #45 feat(skills): Add GitHub domain skills (PR, awaiting review)

### Pending my review (2 PRs)
- #46 feat(installer): Go CLI (by @coauthor, opened 1d ago)

### Recent activity (last 7 days)
- #45 PR merged (3d ago)
- #43 Issue closed (5d ago)
```

If everything is clean: _"No open items assigned to you and no pending reviews."_

## 3. Scope Override for Agents

Agents can override the default scope in their own instructions:
- **Developer agent**: Current repo only
- **PO agent**: Org-wide scope
- **Team lead agent**: Specific set of repos

The skill respects whatever scope is active.

### Anti-Patterns

- Querying org-wide without explicit user request (too noisy)
- Showing raw JSON output instead of formatted summary
- Not identifying current user before querying
- Hardcoding org or repo names (detect from context)
- Including empty sections in output

### Relevant GitHub CLI Commands

```bash
# Get current user
gh api user --jq '.login'

# Get current repo
gh repo view --json owner,name

# Issues assigned to me (current repo)
gh issue list --assignee @me --state open --json number,title,labels,updatedAt

# PRs authored by me (current repo)
gh pr list --author @me --state open --json number,title,reviewDecision,updatedAt

# PRs where my review is requested (current repo)
gh pr list --search "review-requested:@me" --state open --json number,title,author,updatedAt

# Unassigned issues (current repo)
gh issue list --search "no:assignee" --state open --json number,title,labels,createdAt

# Recent activity (last N days, current repo)
# Bash/Linux/Mac:
gh issue list --state all --search "updated:>=$(date -d 'N days ago' +%Y-%m-%d)" --json number,title,state,updatedAt
gh pr list --state all --search "updated:>=$(date -d 'N days ago' +%Y-%m-%d)" --json number,title,state,updatedAt

# PowerShell/Windows:
$since = (Get-Date).AddDays(-N).ToString("yyyy-MM-dd")
gh issue list --state all --search "updated:>=$since" --json number,title,state,updatedAt
gh pr list --state all --search "updated:>=$since" --json number,title,state,updatedAt

# Org-wide queries (use GraphQL)
# Issues assigned to user in org
gh api graphql -f query='
  query($login: String!) {
    search(query: "is:issue is:open assignee:{login} org:{org}", type: ISSUE, first: 30) {
      nodes {
        ... on Issue {
          number title
          repository { nameWithOwner }
          labels(first: 5) { nodes { name } }
          updatedAt
        }
      }
    }
  }
' -f login={username}

# PRs authored by user in org
gh api graphql -f query='
  query($login: String!) {
    search(query: "is:pr is:open author:{login} org:{org}", type: ISSUE, first: 30) {
      nodes {
        ... on PullRequest {
          number title
          repository { nameWithOwner }
          reviewDecision
          updatedAt
        }
      }
    }
  }
' -f login={username}

# PRs where user review is requested in org
gh api graphql -f query='
  query($login: String!) {
    search(query: "is:pr is:open review-requested:{login} org:{org}", type: ISSUE, first: 30) {
      nodes {
        ... on PullRequest {
          number title
          repository { nameWithOwner }
          author { login }
          updatedAt
        }
      }
    }
  }
' -f login={username}

# Unassigned issues in org
gh api graphql -f query='
  query {
    search(query: "is:issue is:open no:assignee org:{org}", type: ISSUE, first: 30) {
      nodes {
        ... on Issue {
          number title
          repository { nameWithOwner }
          labels(first: 5) { nodes { name } }
          createdAt
        }
      }
    }
  }
'
```
