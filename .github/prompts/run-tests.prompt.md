---
agent: test-qa
tools: ['vscode', 'execute', 'read', 'edit', 'search']
description: 'Execute generated unit test cases and capture results.'
---

Execute the generated unit test cases and capture results with coverage.

## Tasks

### 1. Detect Test Framework
- Identify the project's test framework from config files:
  - **C++**: GoogleTest (`BUILD` files, `CMakeLists.txt`)
  - **Python**: pytest (`pyproject.toml` / `setup.cfg`)
  - **Rust**: cargo test (`Cargo.toml`)
  - **Go**: go test (`testing` package, `_test.go` files)

### 2. Execute Tests with Coverage
- Run the appropriate test command with coverage enabled:
  - C++: `bazel test //:all --test_summary=detailed` or `ctest --output-on-failure`
  - Python: `pytest --cov=src --cov-report=term-missing -v`
  - Rust: `cargo tarpaulin --out Html` or `cargo test --verbose`
  - Go: `go test -cover ./...` or `go test -coverprofile=coverage.out ./...`

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
