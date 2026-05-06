---
agent: release-pr
tools: ['read', 'edit', 'github-enterprise/*']
description: 'Evaluate RELEASE phase quality, assign a score, update score.md, and produce final SDLC scorecard.'
---

Evaluate the RELEASE phase and produce a quantitative score. As the final phase, also compute the Overall SDLC Score.

## Evaluation Criteria

| Criterion | Weight | What to Check |
|-----------|--------|---------------|
| Code review completeness | 50% | All critical/high issues from `release-review` resolved |
| PR quality | 50% | Clear description, linked JIRA ticket, proper labels, reviewers assigned |

## Score Thresholds

| Score (out of 10) | Rating |
|-------------------|--------|
| < 7 | 🔴 Red — Below standard, needs rework |
| 7 | 🟡 Yellow — Acceptable, proceed with caution |
| > 7 | 🟢 Green — Good to go |

## Tasks

### 0. Artifact Existence Verification (MANDATORY FIRST STEP)
Attempt to read each file below. Log existence status (Y/N). Do NOT assume content.
- `.stage/<JIRA-ID>/review-backlog.md` (if review loop was run)
- PR exists and is accessible?
- `.stage/score.md` (previous phase scores)
If no PR exists → score PR quality as 0.

### 1. Read Phase Artifacts
- Read `.stage/<JIRA-ID>/review-backlog.md` (if exists)
- Review PR details (title, description, labels, reviewers)
- Check commit history format

### 1b. Cross-Validation
- Does the PR title contain the Jira ticket ID?
- Does the PR description reference the requirements from plan.md?
- Are all critical/high issues from review-backlog.md marked as resolved?
- Do commit messages follow the `<type>(<scope>): <description>` format?
Flag inconsistencies in the Gaps section.

### 2. Score Each Criterion
- Evaluate each criterion against actual artifacts
- If an artifact is missing, score that criterion as 0
- Calculate the weighted average for the final score

### 3. Create Phase Score File
Save to `.stage/<JIRA-ID>/release-score.md` with:
- JIRA ID, Phase (RELEASE), Score, Timestamp
- Evaluation breakdown table
- Strengths, Gaps, Recommendation

### 4. Update Global Score Logger
- If `.stage/score.md` does not exist, create it with header
- If RELEASE row already exists (re-run), update it in place
- If RELEASE row does not exist, append it

### 5. Compute Overall SDLC Score
- Read all rows from `score.md`
- Calculate the average score across all completed phases
- Update the "Overall Score" section at the bottom of `score.md`:

```markdown
## Overall Score: <average> / 10 (<Rating>)
```

- Present the final scorecard to the user as part of the SDLC completion summary

## Rules
- Score ONLY what the artifacts prove. If information is absent, score it as missing — never infer.
- Never inflate scores. A missing artifact = 0 for that criterion.
- Present the complete scorecard to the user before closing the SDLC cycle.
- This prompt may be run independently by the user for a second opinion. Evaluate as if you did NOT produce the artifacts.
