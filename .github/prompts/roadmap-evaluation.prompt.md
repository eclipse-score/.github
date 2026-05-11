---
agent: plan-community-roadmap
tools: ['read', 'edit', 'search']
description: 'Evaluate roadmap planning quality and update score artifacts.'
---

Evaluate roadmap planning quality and produce a score report.

## Criteria
| Criterion | Weight | What to Check |
|-----------|--------|---------------|
| Context completeness | 25% | Related issues and dependencies captured? |
| Community alignment | 25% | Evidence of discussion and contributor interest documented? |
| Scope quality | 25% | In-scope/out-of-scope clear and realistic? |
| Task readiness | 25% | Tasks are vertical, actionable, and sequenced? |

## Tasks
1. Verify required artifacts exist:
   - `.stage/ROADMAP-XXX/issue-summary.md`
   - `.stage/ROADMAP-XXX/community-alignment.md`
   - `.stage/ROADMAP-XXX/roadmap.md`
2. Score each criterion from 0-100 and compute weighted total.
3. Write evaluation to `.stage/ROADMAP-XXX/roadmap-score.md` with strengths and gaps.
4. Update `.stage/score.md` with a ROADMAP phase row.
5. Present score before confirmation gate.

## Rules
- If an artifact is missing, score affected criterion as 0 and note the gap.
- Re-run evaluation on retries and overwrite `roadmap-score.md`.
