---
agent: build-compile
tools: ['vscode', 'execute', 'read', 'search']
description: 'Run comprehensive verification loop before creating a pull request. Build, lint, test, and security checks.'
---

Run a comprehensive pre-PR verification loop to ensure code is ready for review.

## Verification Steps (execute in order)

### 0. Environment Check
- Prefer the repository devcontainer when one is provided.
- For SCORE-style middleware repositories, treat Bazel as the central build entry point unless the codebase proves otherwise.

### 1. Build Check
- Run the project build command
- **PASS criteria**: Zero compilation errors
- If FAIL: Stop and report. Use `build-fix.prompt.md` to resolve.

### 2. Type Check (if applicable)
- C++: Type checking via compiler flags (`-Werror`)
- Python: `mypy src/`
- Rust: `cargo check`
- Go: `go build ./...`
- **PASS criteria**: Zero type errors

### 3. Lint Check
- Run the project linter:
  - C++: `bazel test //:format.check`
  - Python: `ruff check .` or `flake8 .`
  - Rust: `cargo clippy --all-targets`
  - Go: `go vet ./...`
- **PASS criteria**: Zero lint errors or warnings

### 4. Test Check
- Run the full test suite:
  - C++: `bazel test //:all` or `ctest`
  - Python: `pytest --cov=src --cov-report=term-missing`
  - Rust: `cargo test --verbose`
  - Go: `go test -cover ./...`
- **PASS criteria**: All tests pass, coverage ≥ 80%

### 4b. Documentation Check (if applicable)
- If documentation or traceability assets changed, run the repository's documented docs-as-code verification command or Bazel docs target.
- For SCORE-style repos, expect Sphinx and sphinx-needs based docs assets under `docs/`.
- **PASS criteria**: Documentation validation passes with zero errors

### 5. Security Audit
- Check for hardcoded secrets: scan for API keys, passwords, tokens in changed files
- Check dependency vulnerabilities:
  - Python: `pip-audit`
  - Rust: `cargo audit`
  - Go: `nancy` or `go mod verify`
  - C++: OWASP Dependency-Check if configured
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
| Docs | PASS/FAIL/N/A | Validation result or not applicable |
| Types | PASS/FAIL/N/A | Error count or clean |
| Lint | PASS/FAIL | Warning/error count |
| Tests | PASS/FAIL | Pass/fail/skip counts, coverage % |
| Security | PASS/FAIL | Findings count |
| Git | PASS/FAIL | Clean/dirty, commit format |

**Overall: PASS / FAIL**

## Rules
- Run ALL checks even if an earlier one fails (report all issues at once)
- Save report to `.stage/<ISSUE-ID>/verification-report.md` if GitHub Issues context exists
- Do NOT proceed to PR creation if any check is FAIL
- Present report for user review before recommending next steps
