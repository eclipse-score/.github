---
agent: code-architect
tools: ['read', 'edit', 'search', 'todo']
description: 'Evaluate architecture phase output quality and save score.'
---

Evaluate the quality of architecture outputs produced during this phase.

## Evaluation Criteria

| Criterion | Weight | What to Check |
|-----------|--------|---------------|
| Decision Completeness | 20% | All key architecture decisions captured with context, rationale, and alternatives? |
| ADR Correctness | 20% | ADRs follow the project MADR format? Statuses accurate? |
| Boundary Clarity | 20% | Boundaries explicit, enforceable, and grounded in the codebase? |
| Traceability | 20% | Each decision traced to a requirement or business constraint? |
| Pragmatism | 20% | Recommendations grounded in actual codebase, not theoretical? |

## Score Thresholds

| Score (out of 10) | Rating |
|-------------------|--------|
| < 7 | 🔴 Red — Below standard, needs rework |
| 7 | 🟡 Yellow — Acceptable, proceed with caution |
| > 7 | 🟢 Green — Good to go |

## Tasks

### 0. Artifact Existence Verification (MANDATORY FIRST STEP)
Attempt to read each file below. Log existence status (Y/N). Do NOT assume content.
- `.stage/docs/architecture.md` (if created/updated)
- Any new ADRs in `docs/adr/`
- Architecture review findings (if `/arch review` was run)
- Architecture health report (if `/arch evolve` was run)
If no architecture artifacts exist → score ALL criteria as 0.

### 1. Read Phase Artifacts
- Read all architecture artifacts found in Step 0.

### 1b. Cross-Validation
- Do module/service names in architecture.md match actual codebase directories?
- Do ADR decisions reference real technology choices present in the project?
- Are boundary definitions enforceable with the project's actual dependency structure?
Flag inconsistencies in the Gaps section.

### 2. Score Each Criterion
- Evaluate each criterion against actual artifacts only
- If an artifact is missing, score that criterion as 0
- Calculate the weighted average for the final score

### 3. Create Phase Score File
Save to `.stage/<JIRA-ID>/arch-score.md`:

```markdown
# Architecture Evaluation — <JIRA-ID>

**Phase:** Architecture
**Score:** <X> / 10 (<Rating>)
**Evaluated at:** <timestamp>

| Criterion | Weight | Score | Evidence |
|-----------|--------|-------|----------|
| Decision Completeness | 20% | <X>/10 | ... |
| ADR Correctness | 20% | <X>/10 | ... |
| Boundary Clarity | 20% | <X>/10 | ... |
| Traceability | 20% | <X>/10 | ... |
| Pragmatism | 20% | <X>/10 | ... |

## Strengths
- <what went well>

## Gaps
- <what is missing or weak>

## Recommendation
<PROCEED | PROCEED WITH CAUTION | REWORK REQUIRED>
```

### 4. Update Global Score Logger
- If `.stage/score.md` does not exist, create it with header
- If ARCH row already exists (re-run), update it in place
- If ARCH row does not exist, append it

## Rules
- Score ONLY what the artifacts prove. If information is absent, score it as missing — never infer.
- Never inflate scores. A missing artifact = 0 for that criterion.
- Present the score to the user before proceeding.
- This prompt may be run independently by the user for a second opinion. Evaluate as if you did NOT produce the artifacts.
