---
agent: code-implement
tools: ['vscode', 'read', 'edit', 'search']
description: 'Evaluate CODE phase quality, assign a score, and update the global score.md.'
---

Evaluate the CODE phase and produce a quantitative score.

## Evaluation Criteria

| Criterion | Weight | What to Check |
|-----------|--------|---------------|
| Architecture alignment | 50% | Design follows existing patterns, ADR documented if applicable |
| Implementation completeness | 50% | All requirements from `plan.md` addressed, no partial implementations |

## Score Thresholds

| Score (out of 10) | Rating |
|-------------------|--------|
| < 7 | 🔴 Red — Below standard, needs rework |
| 7 | 🟡 Yellow — Acceptable, proceed with caution |
| > 7 | 🟢 Green — Good to go |

## Tasks

### 0. Artifact Existence Verification (MANDATORY FIRST STEP)
Attempt to read each file below. Log existence status (Y/N). Do NOT assume content.
- `.stage/<JIRA-ID>/plan.md`
- `.stage/<JIRA-ID>/implementationReport.md`
If any required artifact is missing → score affected criteria as 0 and log in Gaps.

### 1. Read Phase Artifacts
- Read `.stage/<JIRA-ID>/plan.md` for requirements
- Read `.stage/<JIRA-ID>/implementationReport.md`
- Review modified source files

### 1b. Cross-Validation
- Does every requirement in plan.md have a corresponding implementation mentioned in implementationReport.md?
- Do file paths referenced in implementationReport.md actually exist in the codebase?
- Are any requirements from plan.md missing from the implementation?
Flag inconsistencies in the Gaps section.

### 2. Score Each Criterion
- Evaluate each criterion against actual artifacts and code
- If an artifact is missing, score that criterion as 0
- Calculate the weighted average for the final score

### 3. Create Phase Score File
Save to `.stage/<JIRA-ID>/code-score.md` with the same structure as plan-score.md:
- JIRA ID, Phase (CODE), Score, Timestamp
- Evaluation breakdown table
- Strengths, Gaps, Recommendation

### 4. Update Global Score Logger
- If `.stage/score.md` does not exist, create it with header
- If CODE row already exists (re-run), update it in place
- If CODE row does not exist, append it

## Rules
- Score ONLY what the artifacts prove. If information is absent, score it as missing — never infer.
- Never inflate scores. A missing artifact = 0 for that criterion.
- Present the score to the user before proceeding.
- This prompt may be run independently by the user for a second opinion. Evaluate as if you did NOT produce the artifacts.
