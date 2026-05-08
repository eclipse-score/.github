---
agent: build-compile
tools: ['read', 'edit']
description: 'Evaluate BUILD phase quality, assign a score, and update the global score.md.'
---

Evaluate the BUILD phase and produce a quantitative score.

## Evaluation Criteria

| Criterion | Weight | What to Check |
|-----------|--------|---------------|
| Compilation success | 50% | Zero build errors |
| Lint compliance | 50% | Zero lint errors or warnings |

## Score Thresholds

| Score (out of 10) | Rating |
|-------------------|--------|
| < 7 | 🔴 Red — Below standard, needs rework |
| 7 | 🟡 Yellow — Acceptable, proceed with caution |
| > 7 | 🟢 Green — Good to go |

## Tasks

### 0. Artifact Existence Verification (MANDATORY FIRST STEP)
Attempt to read each file below. Log existence status (Y/N). Do NOT assume content.
- `.stage/<ISSUE-ID>/buildReport.md`
If the artifact is missing → score ALL criteria as 0.

### 1. Read Phase Artifacts
- Read `.stage/<ISSUE-ID>/buildReport.md`
- Review build output logs

### 1b. Cross-Validation
- Does buildReport.md contain actual build command output (not just "build passed")?
- Are lint warnings listed individually or just a count?
- Do any build warnings reference files that don't exist in the codebase?
Flag inconsistencies in the Gaps section.

### 2. Score Each Criterion
- Evaluate each criterion against actual build results
- If a check was not run or artifact is missing, score that criterion as 0
- Calculate the weighted average for the final score

### 3. Create Phase Score File
Save to `.stage/<ISSUE-ID>/build-score.md` with:
- ISSUE ID, Phase (BUILD), Score, Timestamp
- Evaluation breakdown table
- Strengths, Gaps, Recommendation

### 4. Update Global Score Logger
- If `.stage/score.md` does not exist, create it with header
- If BUILD row already exists (re-run), update it in place
- If BUILD row does not exist, append it

## Rules
- Score ONLY what the artifacts prove. If information is absent, score it as missing — never infer.
- Never inflate scores. A missing artifact = 0 for that criterion.
- Present the score to the user before proceeding.
- This prompt may be run independently by the user for a second opinion. Evaluate as if you did NOT produce the artifacts.
