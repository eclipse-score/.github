---
agent: code-fix
tools: ['vscode', 'execute', 'read', 'edit', 'search']
description: 'Incrementally fix build and type errors with minimal, safe changes. One error at a time.'
---

Diagnose and fix build failures incrementally.

## Step 1: Detect Build System
- Identify the project's build tool from project files:
  - **C++**: Bazel (`BUILD` files, `MODULE.bazel`, `.bazelversion`) as the primary build system; CMake only if the repo explicitly uses it without Bazel
  - **Python**: pip (`requirements.txt`), poetry (`pyproject.toml`)
  - **Rust**: Cargo (`Cargo.toml`)
  - **Go**: Go modules (`go.mod`)
- If a devcontainer exists, prefer reproducing failures there before applying fixes.

## Step 2: Run Build and Capture Errors
- Execute the appropriate build command:
  - C++: `bazel build //...` by default; use `cmake --build build` only if the repo has no Bazel build entry point
  - Python: `python -m py_compile <file>` or `mypy src/`
  - Rust: `cargo build`
  - Go: `go build ./...`
- Capture full error output

## Step 2b: Handle Docs-As-Code Failures (if applicable)
- If the failure comes from documentation or traceability assets, run the repository's documented docs verification command or Bazel docs target.
- For SCORE-style repositories, assume Sphinx and sphinx-needs are the primary docs stack unless the repo proves otherwise.

## Step 3: Parse and Fix ONE Error
- Extract the **first** error from the build output
- Classify the error type:
  - **Compilation** — Syntax, type mismatch, missing imports
  - **Dependency** — Missing packages, version conflicts
  - **Configuration** — Invalid config, missing environment variables
  - **Lint** — clippy, ruff, go vet, clang-format violations
  - **Test** — Failing tests blocking build
- Read the failing file and surrounding context
- Apply the **minimal fix** — prefer single-line changes
- Prefer upstream root-cause fixes over downstream workarounds

## Step 4: Verify Fix
- Re-run the build command
- Confirm the fixed error is resolved
- Check that no NEW errors were introduced

## Step 5: Repeat or Report
- If more errors remain: present the next error and repeat from Step 3
- If build passes: report success with summary

## Summary Report
After all errors resolved:
- Total errors fixed
- Fix descriptions (file, line, what changed)
- Final build status: PASS

## Rules
- **One error at a time** — never batch-fix multiple errors
- **Minimal changes** — smallest possible edit to resolve
- **No suppression without approval** — never add `@SuppressWarnings`, `// eslint-disable`, `# noqa` without asking
- **Verify after each fix** — always re-run build
- Reference `.github/instructions/` files for language-specific standards
