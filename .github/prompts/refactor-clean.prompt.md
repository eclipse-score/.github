---
agent: code-refactor
tools: ['vscode', 'execute', 'read', 'edit', 'search']
description: 'Safely identify and remove dead code with test verification at every step.'
---

Identify and safely remove dead code from the codebase.

## Step 1: Scan for Dead Code
- Search for unused imports, variables, functions, classes, and files
- Use language-appropriate detection:
  - **C++**: unused variable warnings via compiler flags
  - **Python**: `vulture`, `pylint` unused warnings
  - **Rust**: `cargo clippy` unused code warnings
  - **Go**: `go vet` with unused analysis

## Step 2: Categorize by Safety Tier
- **Tier 1 (Safe)**: Unused imports, unused local variables, commented-out code
- **Tier 2 (Low Risk)**: Private methods/functions with zero callers
- **Tier 3 (Medium Risk)**: Exported/public functions with zero callers in codebase
- **Tier 4 (High Risk)**: Entire files or modules with zero imports

## Step 3: Present Candidates One at a Time

**Dead Code Candidate:**
- **File:** `path/to/File:L42-L58`
- **Type:** Unused import | Dead function | Commented code | Orphan file
- **Safety Tier:** 1-4
- **Evidence:** Zero references found, no callers detected
- **Options:**
  1. Remove — Delete the dead code
  2. Skip — Keep it
  3. Investigate — Show all potential callers/references

## Step 4: Remove and Verify
For each approved removal:
1. Delete the dead code
2. Run build — verify no breakage
3. Run tests — verify all pass
4. If build/tests fail: **immediately revert** and report

## Step 5: Summary Report
- Lines removed by category (imports, functions, files)
- Build status: PASS / FAIL
- Test status: PASS / FAIL
- Total cleanup impact

## Rules
- **Verify after each removal** — build + tests must pass
- **Never remove Tier 3/4 without explicit user approval**
- **Immediately revert** if removal causes breakage
- **Commented-out code is dead code** — remove unless it has a linked TODO/FIXME with GitHub issue
- Reference `.github/instructions/clean-code.instructions.md` for quality standards
