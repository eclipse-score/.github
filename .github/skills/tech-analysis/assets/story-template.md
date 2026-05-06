# Story Template

Use this template when generating vertically sliced user stories from technical analysis.

```markdown
# Story: [Prefix]-[N] — [Short Title]

**Parent Epic**: EPIC-XXX
**Service/Module**: [Which repo/service this story lives in]
**Story Points**: [1 / 2 / 3 / 5 / 8]

## What
[One paragraph: what this story delivers. Describe the user-visible or system-visible outcome.]

## Why
[One paragraph: why this story matters. Link to the business value from the Epic.]

## Acceptance Criteria

### AC-1: [Happy Path]
- **Given** [precondition]
- **When** [user/system action]
- **Then** [expected outcome]

### AC-2: [Error/Edge Case]
- **Given** [error condition or edge case]
- **When** [user/system action]
- **Then** [expected error handling or graceful behavior]

### AC-3: [Additional Criterion]
- **Given** [precondition]
- **When** [action]
- **Then** [outcome]

## Files Affected
- `path/to/file1.ext` — [What changes: new file / modify / extend]
- `path/to/file2.ext` — [What changes]

## Dependencies
- **Depends on**: [Other stories that must be completed first, or "None"]
- **Blocks**: [Stories that depend on this one, or "None"]
- **External**: [External team/service dependencies, or "None"]

## Out of Scope
- [What is explicitly NOT included in this story]

## Technical Notes
- [Key implementation hints derived from codebase analysis]
- [Patterns to follow based on similar implementations found in repo]
- [Integration points to be aware of]
```

## Vertical Slicing Rules
- Each story MUST deliver a complete vertical slice (end-to-end within one service/module)
- Each story MUST be independently deployable and testable
- Each story MUST be completable within one sprint (if > 8 story points, split further)
- Stories within the same service should be ordered by dependency
- No "backend-only" or "frontend-only" stories -- each slice should deliver observable value
