You are operating inside the SCORE governance overlay.

This file is runtime-specific glue.
Canonical, runtime-neutral policy should live in AGENTS.md.

This repository intentionally keeps only SCORE-specific governance contracts and lightweight maintenance rules.
Generic workflow execution (for example Spec Kit, OpenSpec, BMAD, or custom runtime behavior) is inherited externally by adopter repositories.

## Responsibilities

1. Preserve issue-first traceability.
2. Preserve SCORE-specific contracts:
   - `.github/references/repo-manifest.schema.json`
   - `.github/references/agent-card.schema.json`
   - `.github/score/repo-manifest.json`
3. Keep maintenance burden low by avoiding broad framework content in this repo.

Terminology note: `.github/references/agent-card.schema.json` defines a SCORE work/handoff artifact, not an A2A service-discovery AgentCard.

## Scope

- Keep local content focused on SCORE-specific policy and schema contracts.
- Avoid embedding large generic agent/prompt catalogs.
- Prefer placeholders for runtime-specific naming:
  - `<ASSISTANT_INSTRUCTIONS_FILE>`
  - `<AI_ASSISTANT_NAME>`
  - `<AI_REVIEW_BOT>`

## Artifact Rules

- Use issue-scoped folders for work artifacts:
  - `.stage/ISSUE-<number>/...`
- Never create anonymous stage artifacts at repository root.

## SDLC Progress Block

When status tracking is needed, use this block:

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
- Roadmap planning is optional.
- Most single issues go directly to requirements and implementation.

## Governance Rules

- Keep policy files concise and deterministic.
- Keep generated or inherited framework artifacts outside this repository, or produce them from a renderer in adopter repos.
- Run markdown hygiene checks before merge.
