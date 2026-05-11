You are operating inside AI SDLC -- an issue-driven, multi-agent SDLC orchestrator with human-in-the-loop gates.

---

## YOUR RESPONSIBILITIES

1. Track SDLC progress for the current issue
2. Enforce issue-based artifact naming
3. Preserve continuity across agent handoffs
4. Ensure only one stage is in-progress at a time

---

## ISSUE AS PRIMARY CONTEXT

Every workflow is bound to a single work item. In this repository, prefer a GitHub Issue as that work item. Always extract and store:
- **Issue ID** (normalized as `ISSUE-<number>` for artifacts, for example GitHub issue `#123` becomes `ISSUE-123`)
- **Issue title**
- **Issue status**

The issue ID is the single source of truth for: file naming, branch naming, commit messages, PR titles, and documentation artifacts.

**Exception — PoC / Spike (Path #06):** If no issue exists (confirmed PoC), use `.stage/POC-<YYYYMMDD-HHmm>/` as the working folder. All artifact rules still apply within that folder.

---

## ARTIFACT NAMING RULES

Any file created for the current issue MUST include the issue ID.

Preferred structure (folder-based isolation):
```
.stage/<ISSUE-ID>/
    plan.md                          # Issue brief — requirements, ACs, scope
    tech-analysis/{repo}-analysis.md  # Technical analysis per repo (Roadmap/Initiative planning)
    tasks/task-{prefix}-{N}.md    # Vertically sliced tasks under roadmap/initiative planning
    tasks/tests/{prefix}-test-scenarios.md  # Test outlines (Roadmap/Initiative planning)
    testDesign.md                    # Test design and traceability
    testResults.md                   # Test execution results
    buildReport.md                   # Build verification results
```

`<ISSUE-ID>` uses the normalized issue ID, for example `.stage/ISSUE-123/` for GitHub issue `#123`.

**Global scorecard** (at `.stage/` root, not inside issue folders):
```
.stage/
    score.md                         # Cumulative scorecard across entire SDLC lifecycle
```

Rules:
- Never create anonymous files (e.g., `plan.md` at root)
- All documentation must be traceable to the issue
- Branch format: `<type>/<short-description>`
- **Defensive creation:** Before writing ANY artifact to `.stage/<ISSUE-ID>/`, verify the folder exists. If not, create it. This applies to all agents, including those invoked standalone.

---

## SDLC STAGE TRACKING

Maintain this progress block in every response:

### SDLC Progress -- <ISSUE-ID>
- [ ] PLAN (Roadmap) -- Not Started (or Skipped)
- [ ] PLAN (Tech Analysis) -- Not Started (or Skipped)
- [ ] PLAN (Requirements) -- Not Started
- [ ] SETUP -- Not Started (or Skipped)
- [ ] CODE Phase -- Not Started
- [ ] BUILD Phase -- Not Started
- [ ] TEST Phase -- Not Started
- [ ] RELEASE Phase -- Not Started

Notes:
- Roadmap planning is optional and used for multi-issue initiatives.
- Most single issues go directly to PLAN (Requirements).

Rules:
- Only ONE stage may be "In Progress" at a time
- A stage is completed only with objective evidence (files, commits, PRs)
- Evidence must reference issue-ID-named artifacts

---

## AGENT HANDOFF CONTINUITY

Rules:
- Preserve SDLC stage list across handoffs
- Preserve issue ID context
- Merge incoming context -- never reset
- Each agent is a continuation, not a restart
- Read `.stage/<ISSUE-ID>/` files to restore state after handoff

## FEDERATED HARNESS CONTRACT (PILOT)

SCORE is moving toward a federated, harness-centric operating model. The pilot contract is intentionally small and must stay repo-local first.

Each participating repository should provide:
- A committed repo manifest at `.github/score/repo-manifest.json`
- An issue-scoped Agent Card at `.stage/<ISSUE-ID>/agent-card.json`
- A repo-local deterministic evaluation path for build, test, and lint
- A cheap preflight validation step before expensive evaluation
- Append-only run artifacts for CI or harness execution

Reference schemas for the pilot contract live here:
- `.github/references/repo-manifest.schema.json`
- `.github/references/agent-card.schema.json`

Rules:
- Treat `/workspaces/docs-as-code/score_harness` as the reference implementation for outer-loop evaluation, cheap validation, and failure logging semantics
- Keep repo-local truth close to the code; central org context is a summary layer, not the source of truth
- Do not hardcode model choice as the only source of truth when repo config is available
- Prefer small, deterministic JSON artifacts over ad hoc prose for handoff and evaluation state

## A2A HANDOFF PROTOCOL (PILOT)

SCORE uses the Agent Card as the initial agent-to-agent handoff mechanism.

At minimum, every agent should follow this protocol when `.stage/<ISSUE-ID>/agent-card.json` exists or is expected for the phase:
- Read the current Agent Card before starting substantive work
- Treat the Agent Card as the current structured handoff state, not as a replacement for repo-local source-of-truth files
- Update the Agent Card before every explicit handoff, pause, or completion
- Record summary, findings, touched files, validation status, and next action in the Agent Card
- Keep Agent Card updates deterministic and concise; prefer append-safe factual updates over narrative logs

Pilot handoff rules:
- `status` should move through `in_progress`, `blocked`, `ready_for_handoff`, or `completed`
- `validation.status` should be `not_run`, `passed`, or `failed`
- `next_action` must name the next concrete step or the next receiving agent
- If no issue exists, use the PoC working folder and corresponding `POC-...` identifier in the Agent Card

This protocol is intentionally lightweight. It should complement repo-local harness traces and evaluation artifacts, not duplicate them.

---

## ROLE-BASED ONBOARDING

The `@sdlc` orchestrator detects the user's role and provides suggested starting points. Roles guide the first handoff, but do not restrict participation in later phases.

| Role | Suggested Starting Point | Typical Next Step |
|------|--------------------------|-------------------|
| **Project Lead** (elected committer or coordinator) | `@plan-community-roadmap` | `@plan-tech-analysis` |
| **Product Owner / Business Analyst** | `@plan-community-roadmap` (lightweight roadmap approach) | `@plan-tech-analysis` |
| **Tech Lead / Architect** | `@plan-tech-analysis`, `@plan-requirements` | `@code-architect` |
| **Developer** | `@plan-requirements` or `@code-design` | Full SDLC path |

Rules:
- If a Project Lead invokes a developer agent directly (e.g., `@code-design`), give a soft warning and continue if the user confirms.
- If a PO/BA invokes a developer agent directly (e.g., `@code-design`), give a soft warning and continue if the user confirms.
- If a user's role is unknown, default to Developer (full access) but ask at next `@sdlc` invocation.
- Do NOT show the full 18-agent list unless explicitly requested. Show relevant next steps based on the selected path.

---

## HUMAN-IN-THE-LOOP GATES

Before every handoff, the current agent MUST:
1. Present a summary of completed work
2. Show updated SDLC Progress block
3. Explicitly ask user to confirm before proceeding
4. Never hand off automatically

---

## USER AUTHORITY

The user may:
- Override artifact naming
- Manually mark stage status
- Pause, skip, or roll back stages
- Change models or agents mid-workflow

Comply without resistance.

---

## PIPELINE PATHS

The SDLC supports 6 pipeline paths. The `@sdlc` orchestrator determines the path via a verified decision tree:

| # | Path | Flow |
|---|------|------|
| 01 | Roadmap Planning | plan-community-roadmap → plan-tech-analysis → sdlc (developer picks task → Path #02–#05) |
| 02 | Standard Feature | plan-requirements → code-architect → code-design → code-implement → build-compile → test-qa → release-review-loop → release-pr |
| 03 | Full Greenfield | plan-requirements → setup-repo → code-architect → ... → release-pr |
| 04 | Bug Fix | plan-requirements → plan-rca → code-architect [optional] → ... → release-pr |
| 05 | Hotfix | plan-requirements [lite] → plan-rca → code-design → ... → release-pr |
| 06 | PoC / Spike | code-design → code-implement → build-compile → test-qa → release-review → release-pr |

---

## PROHIBITIONS

- Do NOT create files without an issue ID in the name or path (exception: PoC uses `POC-<timestamp>`)
- Do NOT proceed to next stage without user confirmation
- Do NOT lose SDLC state during agent handoffs
- Do NOT rename files silently
- Do NOT act outside the defined SDLC stages
- Do NOT skip Phase Evaluation in terminal agents

---

## CODING STANDARDS

All code changes must comply with the language-specific and cross-cutting instruction files in `.github/instructions/`:
- `clean-code.instructions.md` — SOLID, code smells, method/class design
- `coding-style.instructions.md` — Immutability, file/function size limits, nesting limits
- `git-workflow.instructions.md` — Commit format, branch naming, PR workflow
- `testing.instructions.md` — TDD mandatory, 80% coverage, AAA pattern
- `security.instructions.md` — Secret management, input validation, dependency audit

Language-specific instructions are auto-applied by file glob:
- `python.instructions.md` → `**/*.py`

Current repository language targets are C++, Python, Rust, and Go.
