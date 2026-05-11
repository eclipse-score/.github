# Task Template

Use this template when generating vertically sliced Tasks from technical analysis.

```markdown
# Task: [Prefix]-[N] — [Short Title]

**Parent Initiative**: <INITIATIVE-ID>
**Service/Module**: [Which repo/service this task lives in]
**Size**: [1 / 2 / 3 / 5 / 8]

## What
[One paragraph: what this task delivers. Describe the user-visible or system-visible outcome.]

## Why
[One paragraph: why this task matters. Link to the business value from the initiative context.]

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
- **Depends on**: [Other tasks that must be completed first, or "None"]
- **Blocks**: [Tasks that depend on this one, or "None"]
- **External**: [External team/service dependencies, or "None"]

## Out of Scope
- [What is explicitly NOT included in this task]

## Technical Notes
- [Key implementation hints derived from codebase analysis]
- [Patterns to follow based on similar implementations found in repo]
- [Integration points to be aware of]
```

## Vertical Slicing Rules
- Each task MUST deliver a complete vertical slice (end-to-end within one service/module)
- Each task MUST be independently deployable and testable
- Each task MUST be completable within one sprint (if > 8 size, split further)
- Tasks within the same service should be ordered by dependency
- No "backend-only" or "frontend-only" tasks -- each slice should deliver observable value
