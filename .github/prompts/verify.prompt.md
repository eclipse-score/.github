---
agent: build-compile
tools: ['vscode', 'execute', 'read', 'search']
description: 'Run comprehensive verification loop before creating a pull request. Build, lint, test, and security checks.'
---

Run a comprehensive pre-PR verification loop to ensure code is ready for review.

## Verification Steps (execute in order)

### 1. Build Check
- Run the project build command
- **PASS criteria**: Zero compilation errors
- If FAIL: Stop and report. Use `build-fix.prompt.md` to resolve.

### 2. Type Check (if applicable)
- TypeScript: `npx tsc --noEmit`
- Python: `mypy src/`
- Java: Covered by build step
- **PASS criteria**: Zero type errors

### 3. Lint Check
- Run the project linter:
  - TypeScript/JS: `npx eslint . --max-warnings=0`
  - Python: `ruff check .` or `flake8 .`
  - Java: `mvn checkstyle:check`
  - Angular: `ng lint`
- **PASS criteria**: Zero lint errors or warnings

### 4. Test Check
- Run the full test suite:
  - Java: `mvn test`
  - TypeScript/JS: `npm test -- --coverage`
  - Python: `pytest --cov=src --cov-report=term-missing`
  - Angular: `ng test --watch=false --code-coverage`
- **PASS criteria**: All tests pass, coverage ≥ 80%

### 5. Security Audit
- Check for hardcoded secrets: scan for API keys, passwords, tokens in changed files
- Check dependency vulnerabilities:
  - npm: `npm audit`
  - pip: `pip-audit`
  - Maven: OWASP Dependency-Check if configured
- **PASS criteria**: No critical vulnerabilities, no hardcoded secrets

### 6. Git Status Check
- Verify all changes are committed
- Verify branch is rebased on latest base branch
- Verify commit messages follow format: `type(scope): description`
- **PASS criteria**: Clean working tree, proper commit format

## Verification Report
Produce a summary table:

| Check | Status | Details |
|-------|--------|---------|
| Build | PASS/FAIL | Error count or clean |
| Types | PASS/FAIL/N/A | Error count or clean |
| Lint | PASS/FAIL | Warning/error count |
| Tests | PASS/FAIL | Pass/fail/skip counts, coverage % |
| Security | PASS/FAIL | Findings count |
| Git | PASS/FAIL | Clean/dirty, commit format |

**Overall: PASS / FAIL**

## Rules
- Run ALL checks even if an earlier one fails (report all issues at once)
- Save report to `.stage/<JIRA-ID>/verification-report.md` if Jira context exists
- Do NOT proceed to PR creation if any check is FAIL
- Present report for user review before recommending next steps
