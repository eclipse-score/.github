---
agent: plan-requirements
tools: ['read', 'edit', 'atlassian/*']
description: 'Evaluate PLAN phase quality, assign a score, and update the global score.md.'
---

Evaluate the PLAN phase and produce a quantitative score.

## Evaluation Criteria

| Criterion | Weight | What to Check |
|-----------|--------|---------------|
| Requirements clarity | 50% | SMART requirements extracted, acceptance criteria defined |
| Issue completeness | 50% | All required fields populated (summary, description, priority, acceptance criteria) |

## Score Thresholds

| Score (out of 10) | Rating |
|-------------------|--------|
| < 7 | 🔴 Red — Below standard, needs rework |
| 7 | 🟡 Yellow — Acceptable, proceed with caution |
| > 7 | 🟢 Green — Good to go |

## Tasks

### 0. Artifact Existence Verification (MANDATORY FIRST STEP)
Attempt to read each file below. Log existence status (Y/N). Do NOT assume content.
- `.stage/<ISSUE-ID>/plan.md`
If the artifact is missing → score ALL criteria as 0.

### 1. Read Phase Artifacts
- Read `.stage/<ISSUE-ID>/plan.md`

### 1b. Cross-Validation
- Does the GitHub issue ID in plan.md match the actual GitHub issue?
- Are acceptance criteria testable (each has a verifiable condition)?
- Are requirements SMART (Specific, Measurable, Achievable, Relevant, Time-bound)?
- If parent Epic exists, do the requirements align with Epic scope?
Flag inconsistencies in the Gaps section.

### 2. Score Each Criterion
- Evaluate each criterion against actual artifacts only
- If an artifact is missing, score that criterion as 0
- Calculate the weighted average for the final score

### 3. Create Phase Score File
Save to `.stage/<ISSUE-ID>/plan-score.md`:

```markdown
# PLAN Phase — Score Report

**ISSUE:** <ISSUE-ID>
**Phase:** PLAN
**Score:** <X> / 10 (<Rating>)
**Evaluated at:** <timestamp>

## Evaluation Breakdown

| Criterion | Weight | Score | Notes |
|-----------|--------|-------|-------|
| Requirements clarity | 50% | <X>/10 | <observation> |
| Issue completeness | 50% | <X>/10 | <observation> |

## Strengths
- <what went well>

## Gaps
- <what is missing or weak>

## Recommendation
<PROCEED | PROCEED WITH CAUTION | REWORK REQUIRED>
```

### 4. Update Global Score Logger
- If `.stage/score.md` does not exist, create it with header
- If PLAN row already exists (re-run), update it in place
- If PLAN row does not exist, append it

## Rules
- Score ONLY what the artifacts prove. If information is absent, score it as missing — never infer.
- Never inflate scores. A missing artifact = 0 for that criterion.
- Present the score to the user before proceeding.
- This prompt may be run independently by the user for a second opinion. Evaluate as if you did NOT produce the artifacts.
