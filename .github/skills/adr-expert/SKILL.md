---
name: adr-expert
description: Use when documenting architectural decisions. Enforces the strict "Dual-Trigger" project MADR format.
inference_examples:
  - "Create an ADR for this decision"
  - "Document why we chose Feign"
  - "Write a decision record for the database switch"
---

# ADR Standards

**Trigger**: Request for architectural documentation.

### The Project ADR Format
Always generate ADRs using this exact template. Keep it concise (max 20-30 lines).

```markdown
# ADR-[Number]: [Short Title]

## Status
[Accepted / Proposed / Deprecated]

## Context
[1-2 sentences. What is the problem? Why is a decision needed? e.g. "Teams must bring their own keys..."]

## Decision
[Direct answer. What are we doing? Use bullet points for details.]

## Alternatives considered
[Numbered list of rejected options with brief reason in brackets]
1) [Option 1] (Reason rejected)
2) [Option 2] (Reason rejected)

## Consequences
[Bullet points on impact]
- [Positive/Benefit]
- [Negative/Cost/Risk]
- [Future/Todo]
```

### Writing Rules
- **Conciseness**: No prose walls. Use bullet points.
- **Tone**: Pragmatic and technical.
- **Naming**: `ADR-XXXX-kebab-case-title.md`.
