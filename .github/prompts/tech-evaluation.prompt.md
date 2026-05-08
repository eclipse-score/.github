---
agent: plan-tech-analysis
tools: ['read', 'edit', 'search', 'atlassian/*']
description: 'Evaluate TECH analysis quality, assign a score, and update the global score.md.'
---

Evaluate the TECH analysis phase and produce a quantitative score.

## Evaluation Criteria

| Criterion | Weight | What to Check |
|-----------|--------|---------------|
| Technical depth | 25% | Architecture patterns identified? Integration points mapped? Mermaid workflows included? Similar implementations referenced? |
| Story slicing quality | 25% | Stories vertically sliced? Each story = full stack within one service? Each independently deployable? Story points realistic? |
| Risk identification | 25% | Technical, integration, data, security risks listed? Impact + likelihood + mitigation for each? At least 2 risks per analysis? |
| Completeness | 25% | All affected modules identified? Open questions tracked? Assumptions documented? Dependencies mapped? Coding guidelines referenced? |

## Score Thresholds

| Score (out of 10) | Rating |
|-------------------|--------|
| < 7 | 🔴 Red — Below standard, needs rework |
| 7 | 🟡 Yellow — Acceptable, proceed with caution |
| > 7 | 🟢 Green — Good to go |

## Tasks

### 0. Artifact Existence Verification (MANDATORY FIRST STEP)
Attempt to list/read each location below. Log existence status (Y/N). Do NOT assume content.
- `.stage/EPIC-XXX/tech-analysis/` — at least one `*-analysis.md` file?
- `.stage/EPIC-XXX/stories/` — at least one `story-*.md` file?
- `.stage/EPIC-XXX/stories/tests/` — at least one `*-test-scenarios.md` file?
If any required artifact is missing → score affected criteria as 0 and log in Gaps.

### 1. Read Phase Artifacts
- Read all files in `.stage/EPIC-XXX/tech-analysis/`
- Read all files in `.stage/EPIC-XXX/stories/`
- Read test scenario outlines in `.stage/EPIC-XXX/stories/tests/`

### 1b. Cross-Validation
- Do file/module references in analysis.md actually exist in the codebase? Spot-check at least 3.
- Does every story map to at least one requirement from the Epic?
- Are story point estimates consistent (similar-sized stories have similar points)?
- Does each story have corresponding test scenarios?
Flag inconsistencies in the Gaps section.

### 2. Score Each Criterion
- Evaluate each criterion against actual artifacts only
- If an artifact is missing, score that criterion as 0
- Calculate the weighted average for the final score

### 3. Create Phase Score File
Save to `.stage/EPIC-XXX/tech-score.md`:

```markdown
# TECH Phase — Score Report

**ISSUE:** EPIC-XXX
**Phase:** Technical Analysis
**Score:** <X> / 10 (<Rating>)
**Evaluated at:** <timestamp>

## Evaluation Breakdown

| Criterion | Weight | Score | Notes |
|-----------|--------|-------|-------|
| Technical depth | 25% | <X>/10 | <observation> |
| Story slicing quality | 25% | <X>/10 | <observation> |
| Risk identification | 25% | <X>/10 | <observation> |
| Completeness | 25% | <X>/10 | <observation> |

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
- If TECH row already exists (re-run), update it in place
- If TECH row does not exist, append it

## Rules
- Score ONLY what the artifacts prove. If information is absent, score it as missing — never infer.
- Never inflate scores. A missing artifact = 0 for that criterion.
- Present the score to the user before proceeding.
- If `.stage/EPIC-XXX/tech-score.md` already exists from a previous run, re-evaluate and overwrite it.
- This prompt may be run independently by the user for a second opinion. Evaluate as if you did NOT produce the artifacts.
