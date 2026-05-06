---
agent: plan-tech-analysis
tools: ['read', 'search']
description: 'Auto-detect tech stack, architecture patterns, guidelines, and similar implementations. Save codebase notes.'
---

Perform deep codebase analysis on the confirmed repository.

## Tasks

### 1. Auto-Detect Tech Stack
Scan the repo root for build/config files to identify the stack:
- `pom.xml` / `build.gradle` → Java (Spring Boot, Quarkus, etc.)
- `package.json` → Node.js / TypeScript (React, Angular, Vue, Express, etc.)
- `requirements.txt` / `pyproject.toml` / `setup.py` → Python (Django, FastAPI, Flask, etc.)
- `go.mod` → Go
- `Cargo.toml` → Rust
- `*.csproj` / `*.sln` → .NET
- If multiple found → note as monorepo with multiple modules

### 2. Analyze Architecture Patterns
- **Project structure**: directory layout, module boundaries, layering
- **API patterns**: REST controllers/routes, GraphQL schemas, gRPC protos
- **Database**: migration files (detect tool: Flyway, Alembic, Prisma, Knex, etc.), entity/model definitions
- **Integration points**: HTTP clients, message broker configs, event handlers
- **Configuration**: environment files, config classes, secrets references
- **Security**: auth patterns, role/permission models, middleware

### 3. Scan Coding Guidelines
- Read `.github/instructions/` if it exists
- Read `.editorconfig` if it exists
- Check for linter configs: `.eslintrc`, `checkstyle.xml`, `pylintrc`, `.rubocop.yml`, etc.
- Note active guidelines that the stories must follow

### 4. Find Similar Implementations
- Search the codebase for patterns similar to what the Epic requires
- Look for: existing CRUD operations, similar workflows, integration patterns
- Note file paths and what can be reused as reference

### 5. Save Codebase Notes
Save to `.stage/EPIC-XXX/tech-analysis/{repo-name}-codebase-notes.md`:

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

## API Patterns
- [Detected API style, route conventions, auth patterns]

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
