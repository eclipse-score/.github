---
name: architecture
description: Use when capturing, reviewing, or enforcing architectural decisions. Manages architecture documentation and DRs.
inference_examples:
  - "Initialize architecture documentation"
  - "Review code against architecture decisions"
  - "What are the architectural boundaries?"
  - "Check if this violates our architecture"
---

# Architecture Skill

Manage architectural decisions, enforce boundaries, and maintain living architecture documentation.

## Commands

### `/arch init` — Initialize Architecture Documentation

1. Ask the user about key architectural decisions (interactive, one question at a time):
   - Architecture style (hexagonal, layered, clean, microservices, etc.)
   - Interface style (gRPC, ara::com, SOME/IP, event-driven, CLI-only)
   - Testing strategy (testing-trophy, testing-pyramid)
   - Any additional decisions the team wants to preserve
2. Ask about architectural boundaries (rules to enforce):
   - Example: "Domain layer must not import from infrastructure layer"
3. Generate two files:
   - `.stage/docs/architecture.md` — from the architecture template (see `assets/architecture-template.md`)
   - `docs/design_decisions/DR-001-initial-architecture.md` — first decision record documenting initial decisions

### `/arch review` — Review Code Against Decisions

1. Read `.stage/docs/architecture.md` to load decisions and boundaries.
2. Scan the specified files or current diff.
3. For each boundary rule, check if the code violates it.
4. Report violations with:
   - **Boundary**: Which rule was violated
   - **File:Line**: Where the violation occurs
   - **Fix**: How to resolve it

### `/arch decide` — Record a New Decision

1. Use the `dr-expert` skill to generate a properly formatted DR.
2. Save to `docs/design_decisions/DR-NNN-kebab-case-title.md`.
3. Update `.stage/docs/architecture.md` decisions section if the decision affects architecture-level concerns.

### `/arch evolve` — Check for Drift

1. Read `.stage/docs/architecture.md`.
2. Scan the codebase for patterns that contradict documented decisions.
3. Report inconsistencies and suggest either:
   - Code changes to align with documentation
   - Documentation updates to reflect evolved practices

## Architecture Documentation Schema

See `references/schema.md` for the full YAML schema of `.stage/docs/architecture.md`.

## Architecture Template

See `assets/architecture-template.md` for the full living document template.

## Anti-Patterns

- Making architectural decisions without documenting them
- Ignoring boundary violations in reviews
- Letting architecture documentation go stale
- Documenting decisions after the fact without recording alternatives considered
