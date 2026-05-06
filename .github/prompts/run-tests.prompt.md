---
agent: test-qa
tools: ['vscode', 'execute', 'read', 'edit', 'search']
description: 'Execute generated unit test cases and capture results.'
---

Execute the generated unit test cases and capture results with coverage.

## Tasks

### 1. Detect Test Framework
- Identify the project's test framework from config files:
  - **Java**: JUnit 5 (`pom.xml` / `build.gradle` dependencies)
  - **TypeScript/JS**: Jest or Vitest (`package.json` scripts)
  - **Angular**: Jasmine/Karma (`angular.json` test config)
  - **Python**: pytest (`pyproject.toml` / `setup.cfg`)

### 2. Execute Tests with Coverage
- Run the appropriate test command with coverage enabled:
  - Java: `mvn test jacoco:report`
  - TypeScript/JS: `npx jest --coverage --verbose`
  - Angular: `ng test --watch=false --code-coverage`
  - Python: `pytest --cov=src --cov-report=term-missing -v`

### 3. Capture Results
- Record for each test: name, status (pass/fail/skip), duration
- Capture coverage metrics: overall %, per-module/file breakdown
- Capture any error messages and stack traces for failures

### 4. Analyze Failures
For each failing test:
- Identify root cause: implementation bug vs test bug vs environment issue
- Classify severity: Critical (core logic) | High (feature) | Medium (edge case) | Low (cosmetic)
- Recommend fix approach: fix implementation vs fix test vs skip with justification

### 5. Coverage Assessment
- Compare against thresholds:
  - **80% minimum** overall
  - **100%** for security-critical, auth, and financial code
- Flag uncovered critical paths
- Suggest additional tests for gaps

### 6. Present Results
- Summary table: total, passed, failed, skipped, coverage %
- Failure details with recommended actions
- Do NOT proceed without user review of results
