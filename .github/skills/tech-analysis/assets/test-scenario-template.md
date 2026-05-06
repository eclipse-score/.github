# Test Scenario Outline Template

Use this template when generating lightweight test scenario outlines during story slicing. These are HIGH-LEVEL outlines -- actual test code is written by `@test-qa` during the TEST phase.

```markdown
# Test Scenarios — [Prefix] Stories

**Parent Epic**: EPIC-XXX
**Service/Module**: [Which repo/service]
**Created by**: Tech Analysis Agent (outlines only)

## Story [Prefix]-1: [Story Title]

### Scenario 1: Happy Path
- **Given** [precondition]
- **When** [action]
- **Then** [expected outcome]

### Scenario 2: Error Handling
- **Given** [error condition]
- **When** [action]
- **Then** [graceful failure behavior]

### Scenario 3: Edge Case
- **Given** [boundary condition]
- **When** [action]
- **Then** [expected behavior at boundary]

## Story [Prefix]-2: [Story Title]

### Scenario 1: Happy Path
- **Given** [precondition]
- **When** [action]
- **Then** [expected outcome]

[Repeat for each story]
```

## Rules
- Keep scenarios HIGH-LEVEL: Given/When/Then bullets only
- Do NOT write actual test code, JSON payloads, RBAC matrices, or performance benchmarks
- Do NOT create full Gherkin feature files -- those are `@test-qa`'s job
- Focus on: happy path, error handling, edge cases, and integration boundaries
- Maximum 3-5 scenarios per story
- These outlines serve as INPUT for `@test-qa` during the TEST phase
