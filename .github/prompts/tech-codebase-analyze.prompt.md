---
agent: plan-tech-analysis
tools: ['read', 'search']
description: 'Auto-detect tech stack, architecture patterns, guidelines, and similar implementations. Save codebase notes.'
---

Perform deep codebase analysis on the confirmed repository.

## Tasks

### 1. Auto-Detect Tech Stack
Scan the repo root for build/config files to identify the stack:
- `CMakeLists.txt` / Bazel `BUILD` files → C++
- `requirements.txt` / `pyproject.toml` / `setup.py` → Python
- `go.mod` → Go
- `Cargo.toml` → Rust
- If multiple found → note as monorepo with multiple modules

### 2. Analyze Architecture Patterns
- **Project structure**: directory layout, module boundaries, layering
- **Interface patterns**: gRPC protos, ara::com bindings, SOME/IP/service interfaces, CLI commands, event/message contracts
- **Database**: migration files (detect tool: Flyway, Alembic, Prisma, Knex, etc.), entity/model definitions
- **Integration points**: transport adapters, IPC/service bindings, message broker configs, event handlers, tooling interfaces
- **Configuration**: environment files, config classes, secrets references
- **Security**: platform identity, permissions, mTLS, signing, role/permission models

### 3. Scan Coding Guidelines
- Read `.github/instructions/` if it exists
- Read `.editorconfig` if it exists
- Check for linter configs: `pylintrc`, `.flake8`, `rust-clippy.toml`, `rustfmt.toml`, `golangci.yml`, `.clang-format`, etc.
- Note active guidelines that the tasks must follow

### 4. Find Similar Implementations
- Search the codebase for patterns similar to what the initiative requires
- Look for: existing CRUD operations, similar workflows, integration patterns
- Note file paths and what can be reused as reference

### 5. Save Codebase Notes
Save to `.stage/<INITIATIVE-ID>/tech-analysis/{repo-name}-codebase-notes.md`:

```markdown
# Codebase Notes — {repo-name}

## Tech Stack
- [Detected stack and version]

## Architecture
- [Detected patterns: layered, hexagonal, MVC, etc.]

## Key Modules
| Module/Package | Purpose |
|---------------|---------|
| [path] | [what it does] |

## Database
- [Migration tool, schema patterns, key entities]

## Interface Patterns
- [Detected interface style, contract conventions, transport patterns]

## Integration Points
- [HTTP clients, message brokers, external services]

## Coding Guidelines
- [From .github/instructions/ and linter configs]

## Similar Implementations
- [File paths and what patterns to reuse]
```

Present the codebase notes to the user for confirmation before proceeding.

## Rules
- NEVER assume the tech stack -- detect from actual files
- Do NOT modify any source code in the repository
- If the repo is empty or has no recognizable structure, inform the user
