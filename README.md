# eclipse-score .github repository

This repository hosts the start page when you visit the eclipse-score GitHub organization. It contains links to the Eclipse Score website, documentation, and other resources related to the Eclipse Score project.

The Python tool in this repo now acts as a small repo-overview generator: it collects a cached snapshot of organization metadata once, then renders multiple Markdown views from that shared snapshot.

## Development

Use `uv` to create a virtual environment and install the project dependencies:

```
uv sync --all-groups
```

The CLI now has a built-in overview:

```sh
uv run generate-repo-overview
```

For a cache-only re-render of the profile README and the HTML dashboard:

```sh
uv run generate-repo-overview render-overview
uv run generate-repo-overview render-details
```

For a fresh GitHub pull before rendering, run:

```sh
uv run generate-repo-overview collect
```

By default, `collect` now does a cache-aware refresh: it checks fast, high-level
repository state and reuses cached deep details for repositories whose default
branch SHA has not changed. Use this for regular updates.

For volatile repository metrics (open PRs/issues, release counters, and recent
activity), fast mode keeps a per-repository fetch timestamp and refreshes those
values automatically when they are older than 1 hour.

You can tune this freshness window with `REPO_OVERVIEW_VOLATILE_TTL_MINUTES`
(default: `60`).

If you need a full deep refresh for every repository, run:

```sh
uv run generate-repo-overview collect --deep
```

If you only want the profile README:

```sh
uv run generate-repo-overview render-overview
```

Category order and category descriptions are configured in
`src/generate_repo_overview/profile_readme_config.toml`. Pass
`--config /path/to/file.toml` to use a different config file.

The generator reads repository custom properties from GitHub and expects `GITHUB_TOKEN` to be set. If `GITHUB_TOKEN` is not set, it falls back to `gh auth token`.

Architecture notes for the package live in [src/generate_repo_overview/README.md](src/generate_repo_overview/README.md). The broader design notes are in [docs/repo-overview-tool-design.md](docs/repo-overview-tool-design.md).

To run the local checks:

```sh
uv run pre-commit run --all-files
```

---

## AI SDLC System for Developers

This repository contains the **bootstrap governance** for Eclipse Score's federated, agentic software development lifecycle (SDLC). It is **vendor-neutral** and works with any issue tracker, SCM platform, and LLM.

### Quick Start

#### 1. Use the SDLC in Your Repository

In any SCORE repository, invoke the AI SDLC orchestrator:

```bash
/sdlc
```

Or explicitly:

```bash
/sdlc KICKOFF
```

This launches an interactive workflow that walks you through issue planning, code implementation, testing, and release stages.

#### 2. Set Up a New Repository for SCORE

When creating a new SCORE repository, include:

```bash
# At repo root:
.github/
  ├── copilot-instructions.md      # (copied from this repo)
  ├── instructions/                 # (copied from this repo)
  ├── agents/                        # (copied from this repo)
  ├── prompts/                       # (copied from this repo)
  ├── skills/                        # (copied from this repo)
  └── score/
      └── repo-manifest.json         # (NEW — created per-repo)
```

The manifest declares your repo's language, build commands, and MCP server capabilities. See [repo-manifest schema](/.github/references/repo-manifest.schema.json).

#### 3. Understand Agent Handoffs (A2A Protocol)

Agents communicate via **Agent Cards** — JSON files committed to `.stage/<ISSUE-ID>/agent-card.json`.

**Workflow:**
1. **Agent A** reads `.stage/<ISSUE-ID>/agent-card.json` to restore prior context (no need to re-read session history)
2. Agent A performs work, updates the Card: `status`, `summary`, `findings`, `touched_files`, `validation`
3. Agent A commits the updated Card
4. **Agent B** reads the same Card to resume where A left off
5. Each agent updates the Card before handing off

**Card structure:**
```json
{
  "version": 1,
  "issue_id": "ISSUE-123",
  "repository": "org/repo",
  "goal": "Implement user authentication",
  "status": "in_progress",      // or: blocked, ready_for_handoff, completed
  "summary": "Analyzed requirements, created branch feature/auth-123",
  "findings": ["DB schema needs migration", "Auth library version conflict"],
  "touched_files": ["src/auth.py", "tests/test_auth.py"],
  "validation": {
    "status": "passed",          // or: failed, not_run
    "commands": ["uv run pytest"],
    "errors": []
  },
  "next_action": "Implement password hashing in src/auth.py",
  "trajectory": [
    {"agent": "plan-requirements", "status": "completed", "summary": "..."},
    {"agent": "code-architect", "status": "ready_for_handoff", "summary": "..."}
  ]
}
```

Schema: [agent-card.schema.json](/.github/references/agent-card.schema.json)

### Core Concepts

#### SDLC Stages (Sequential)

1. **PLAN** — Analyze issue requirements, extract acceptance criteria
2. **SETUP** — Prepare repository (if Greenfield) or clone (if Brownfield)
3. **CODE** — Architect design, create implementation plan, write code
4. **BUILD** — Compile, lint, type-check, audit dependencies
5. **TEST** — Generate tests, execute, document coverage
6. **RELEASE** — Review, create PR, finalize

#### Agents

19 agents handle distinct responsibilities. Each:
- Reads the Agent Card to resume context
- Updates the Card during work
- Hands off to the next agent (never auto-proceeds)
- **Model-agnostic** — no hardcoded LLM; your IDE/tooling chooses the model

Key agents:
- `plan-requirements` — Extract requirements from GitHub issue
- `code-architect` — Review arch decisions & design records (DRs)
- `code-design` — Create implementation plan & branch
- `code-implement` — Write production code & docs
- `build-compile` — Verify build, lint, types, dependencies
- `test-qa` — Generate & execute unit tests (TDD-enabled)
- `release-pr` — Create PR, update issue status, complete cycle

#### Tools & MCP

All agents use **generic tool declarations** (no vendor lock-in):

- `github` → Issue tracker (GitHub MCP or `gh` CLI) + SCM
- `read`, `edit`, `search` → Local workspace operations
- `execute` → Run build/test commands
- `agent` → Delegate to another agent

Fallback: If an MCP is unavailable, agents provide **manual CLI commands** and continue.

#### Manifest (Per-Repository)

Each repo declares its execution contract at `.github/score/repo-manifest.json`:

```json
{
  "version": 1,
  "repository": {
    "name": "my-project",
    "language": "python",
    "visibility": "public"
  },
  "bootstrap": {
    "contract_version": "1.0"
  },
  "execution": {
    "build": {
      "command": "uv",
      "args": ["build"]
    },
    "test": {
      "command": "uv",
      "args": ["run", "pytest"]
    },
    "lint": {
      "command": "uv",
      "args": ["run", "ruff", "check", "."]
    }
  },
  "mcp": {
    "server_name": "my-repo-tools",
    "tools": ["build", "test", "lint", "typecheck"]
  }
}
```

Schema: [repo-manifest.schema.json](/.github/references/repo-manifest.schema.json)

### Workflow: Issue → Merged PR

```
1. User creates GitHub issue or invokes /sdlc
2. @plan-requirements fetches issue, extracts requirements
   → Creates .stage/ISSUE-123/plan.md & agent-card.json
3. @code-architect reviews arch decisions (if needed)
   → Reads/updates agent-card.json
4. @code-design creates implementation plan & branch
   → Updates agent-card.json, commits plan
5. @code-implement writes code & docs
   → Pushes branch, updates agent-card.json
6. @build-compile verifies build, lint, types
   → Updates agent-card.json with validation status
7. @test-qa generates & executes tests
   → Updates agent-card.json with coverage
8. @release-review-loop reviews code, fixes issues autonomously
   → Updates agent-card.json after each iteration
9. @release-pr creates PR, closes issue
   → Finalizes agent-card.json, sets status = completed
```

### Roadmap Planning (Optional)

**For Project Leads coordinating multiple related issues:**

If you have **multiple related GitHub issues** that should be planned together (e.g., "authentication subsystem redesign" spans 5 separate issues), use `@plan-community-roadmap`:

```
1. User invokes /sdlc, selects role = "Project Lead"
2. @plan-community-roadmap gathers context from linked issues
   → Verifies community alignment (multiple contributors interested?)
   → Defines scope (in-scope issues, deferred work)
   → Creates .stage/ROADMAP-XXX/ with coordinated task list
3. @plan-tech-analysis breaks roadmap into vertical tasks
   → Creates implementation tasks suitable for parallel work
4. Standard workflow resumes (CODE → BUILD → TEST → RELEASE)
```

**When NOT to use roadmap planning:**
- Single issues → go directly to `/sdlc` (PLAN → CODE → BUILD → TEST → RELEASE)
- Standalone work items that do not need cross-issue coordination

**When to use roadmap planning:**
- Coordinating multiple related issues into a single initiative
- Planning the next version with input from community discussions
- Removing organizational friction around "what work is related"

### Directory Structure

```
.github/
├── copilot-instructions.md    # Central SDLC orchestration policy
├── agents/                     # 19 agent definitions
│   ├── plan-requirements.agent.md
│   ├── code-architect.agent.md
│   └── ...
├── skills/                     # 11 reusable skill modules
│   ├── tech-analysis/
│   ├── dr-expert/
│   └── ...
├── instructions/               # Language/domain-specific rules
│   ├── clean-code.instructions.md
│   ├── python.instructions.md
│   └── ...
├── prompts/                    # Prompt templates (60+)
├── references/                 # JSON Schemas
│   ├── repo-manifest.schema.json
│   └── agent-card.schema.json
└── score/
    └── repo-manifest.json      # This repo's manifest
```

### Getting Help

- **Policy & orchestration**: `.github/copilot-instructions.md`
- **Agent capabilities**: `.github/agents/*.agent.md`
- **Skills & analysis patterns**: `.github/skills/*/SKILL.md`
- **Coding standards**: `.github/instructions/clean-code.instructions.md`
- **Testing requirements**: `.github/instructions/testing.instructions.md`

### Extending SCORE

To add a new agent or skill:

1. Create `.github/agents/my-new-agent.agent.md` or `.github/skills/my-skill/SKILL.md`
2. Follow the format of existing agents/skills
3. Reference the agent/skill in `copilot-instructions.md` if part of the SDLC pipeline
4. Add tests if required

For more details, see [copilot-instructions.md](.github/copilot-instructions.md).
