---
agent: plan-epic-creation
tools: ['read', 'edit', 'atlassian/*']
description: 'Evaluate EPIC creation quality, assign a score, and update the global score.md.'
---

Evaluate the EPIC creation phase and produce a quantitative score.

## Evaluation Criteria

| Criterion | Weight | What to Check |
|-----------|--------|---------------|
| Business case clarity | 25% | Problem statement clear and specific? Business value quantified? "What if we don't build this" answered? Stakeholders identified? |
| Requirements completeness | 25% | All functional requirements listed? Scope clearly bounded? Out-of-scope defined? Dependencies mapped? |
| Acceptance criteria quality | 25% | ACs testable and specific? Given/When/Then format used? Covers happy path AND error/edge cases? |
| Metrics & measurability | 25% | At least 2 success metrics defined? Baseline AND target numbers present? Metrics tied to business outcomes (not technical KPIs)? |

## Score Thresholds

| Score (out of 10) | Rating |
|-------------------|--------|
| < 7 | 🔴 Red — Below standard, needs rework |
| 7 | 🟡 Yellow — Acceptable, proceed with caution |
| > 7 | 🟢 Green — Good to go |

## Tasks

### 0. Artifact Existence Verification (MANDATORY FIRST STEP)
Attempt to read each file below. Log existence status (Y/N). Do NOT assume content — if a file cannot be read, it does not exist.
- `.stage/EPIC-XXX/functional-spec.md`
- `.stage/EPIC-XXX/epic.md`
If any required artifact is missing → score affected criteria as 0 and log in Gaps.

### 1. Read Phase Artifacts
- Read `.stage/EPIC-XXX/functional-spec.md`
- Read `.stage/EPIC-XXX/epic.md`

### 1b. Cross-Validation
- Do stakeholders in epic.md match those in functional-spec.md?
- Are all requirements in functional-spec.md covered by acceptance criteria in epic.md?
- Do scope boundaries (in/out) align between both documents?
- If GitHub Epic exists, does the document title match the GitHub Issues summary?
Flag inconsistencies in the Gaps section.

### 2. Score Each Criterion
- Evaluate each criterion against actual artifacts only
- If an artifact is missing, score that criterion as 0
- Calculate the weighted average for the final score

### 3. Create Phase Score File
Save to `.stage/EPIC-XXX/epic-score.md`:

```markdown
# EPIC Phase — Score Report

**ISSUE:** EPIC-XXX
**Phase:** EPIC Creation
**Score:** <X> / 10 (<Rating>)
**Evaluated at:** <timestamp>

## Evaluation Breakdown

| Criterion | Weight | Score | Notes |
|-----------|--------|-------|-------|
| Business case clarity | 25% | <X>/10 | <observation> |
| Requirements completeness | 25% | <X>/10 | <observation> |
| Acceptance criteria quality | 25% | <X>/10 | <observation> |
| Metrics & measurability | 25% | <X>/10 | <observation> |

## Strengths
- <what went well>

## Gaps
- <what is missing or weak>

## Recommendation
<PROCEED | PROCEED WITH CAUTION | REWORK REQUIRED>
```

### 4. Update Global Score Logger
- If `.stage/score.md` does not exist, create it with header:
  ```
  # Score Tracker — EPIC-XXX
  | Phase | Score | Rating | Date |
  |-------|-------|--------|------|
  ```
- If EPIC row already exists (re-run), update it in place
- If EPIC row does not exist, append it

## Rules
- Score ONLY what the artifacts prove. If information is absent, score it as missing — never infer.
- Never inflate scores. A missing artifact = 0 for that criterion.
- Present the score to the user before proceeding.
- If `.stage/EPIC-XXX/epic-score.md` already exists from a previous run, re-evaluate and overwrite it.
- This prompt may be run independently by the user for a second opinion. Evaluate as if you did NOT produce the artifacts.
