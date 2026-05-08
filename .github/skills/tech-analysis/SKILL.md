---
description: 'Deep technical analysis skill -- codebase-aware, tech-agnostic analysis with gap-only clarification and vertically-sliced story generation.'
---

# Tech Analysis Skill

This skill provides deep technical analysis capabilities. It is loaded on-demand when an agent needs to perform comprehensive codebase analysis for an Epic.

## When to Use
- During PLAN phase: when breaking an Epic into technical analysis and stories
- When user requests deep technical analysis of a feature or epic

## Workflow

### Step 1: Deep Context Analysis (Always Start Here)
Before asking questions, perform thorough analysis:
1. Review Epic artifacts in `.stage/EPIC-XXX/` (functional-spec.md, epic.md)
2. Auto-detect tech stack from repo files (pom.xml, package.json, build.gradle, requirements.txt, go.mod, etc.)
3. Analyze repository structure:
   - Database schemas (migration files -- detect tool automatically)
    - Interface patterns (service contracts, handlers, CLI surfaces, RPC bindings -- detect automatically)
    - Integration patterns (message brokers, transport adapters, gRPC, ara::com, SOME/IP, external tooling -- detect automatically)
   - Configuration and environment patterns
   - Security and authorization patterns
4. Scan coding guidelines: `.github/instructions/`, `.editorconfig`, linter configs
5. Find similar implementations in codebase as reference patterns
6. Identify integration points: dependencies on other services, target platforms, external systems, or shared tooling

### Step 2: Gap-Only Questions
After analysis, identify what you KNOW vs what you DON'T KNOW:
- List knowns (from Epic + codebase) internally
- List unknowns (gaps) internally
- **If no gaps → skip questions entirely, proceed to Step 3**
- If gaps exist: ask ONE question at a time, wait for response
- Provide lettered options (a, b, c, d, e)
- Mark recommended option with "[Recommended]" based on codebase findings
- Explain briefly why you recommend that option with code references

### Step 3: Generate Structured Analysis
Create ONE analysis document per repo in `.stage/EPIC-XXX/tech-analysis/`:

```
tech-analysis/
├── {repo-name}-codebase-notes.md
├── {repo-name}-analysis.md
stories/
├── story-{prefix}-1.md
├── story-{prefix}-2.md
└── tests/
    └── {prefix}-test-scenarios.md
```

### Analysis Document Sections
1. Goal of the Task (business value from Epic)
2. Analysis Summary (modules affected, integration points, interface impacts)
3. Dependencies (team, service, technical, timeline)
4. Architecture Overview with Mermaid diagrams
5. Workflows (current vs future sequence diagrams)
6. Integration Points (detected from actual codebase)
7. Risks (technical risks with impact/mitigation/owner)

## Templates
- `analysis-template.md` -- Per-repo technical analysis structure
- `assets/story-template.md` -- Vertically sliced story structure
- `assets/test-scenario-template.md` -- Lightweight test scenario outlines

## Tech-Agnostic Rules
- NEVER assume a specific tech stack -- detect from repo files
- NEVER reference framework-specific patterns unless found in the actual codebase
- Adapt analysis sections to what exists in the repo (skip sections that don't apply)
- One analysis file per repo -- not hardcoded "backend + frontend"

## Track Throughout
- **Open Questions**: Items where user said "I'm not sure" or "TBD"
- **Assumptions**: Explicit assumptions made during analysis
