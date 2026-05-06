---
agent: plan-rca
tools: ['read', 'edit', 'search', 'atlassian/*']
description: 'Perform ticket-driven root cause analysis. Collect evidence interactively (Hotfix: always ask, Bug Fix: ask if ticket insufficient), generate structured RCA report.'
---

Perform root cause analysis based on the Jira ticket and developer-provided evidence.

## Tasks

### 1. Read Ticket Context
- Read `.stage/<JIRA-ID>/plan.md` for ticket context and path type (Hotfix or Bug Fix)
- Extract any evidence already present: error logs, stack traces, trace IDs, timestamps, affected services

### 2. Collect Evidence (path-dependent)

#### Hotfix Path — Always ask the developer
Hotfix plans are lightweight. Always ask:
1. "Paste the relevant error log output or upload the log file."
2. "Paste the full stack trace from the failing service."
3. "Which environment is affected? (dev / staging / prod)"
4. "When did this first occur? Was there a recent deployment or config change?"
5. "Do you have any trace IDs, request IDs, or correlation IDs?"
6. "How can this be reproduced? (if known)"

Minimum required before proceeding: error log or stack trace + environment + timeline.

#### Bug Fix Path — Check ticket first, ask if insufficient
If ticket already contains error logs + stack trace + affected component → proceed to Step 3.
If insufficient, ask the same 6 questions as the Hotfix path.

Save all collected evidence to `.stage/<JIRA-ID>/rca-evidence.md`.

### 3. Analyze Root Cause
- Correlate all evidence to form hypotheses
- Rank by confidence: High / Medium / Low
- Identify affected components and code paths
- Map to potential fix approaches

### 4. Generate Report
Save structured RCA report at `.stage/<JIRA-ID>/rca-report.md` with:
- Incident summary
- Evidence table (source + details)
- Root cause hypotheses ranked by confidence
- Affected components
- Recommended fix approach for the CODE phase

## Rules
- Never guess without evidence
- If data is missing, ask -- do not assume
- Hotfix path: never skip evidence collection, even if ticket has some data
- At least one High or Medium confidence hypothesis required before proceeding
