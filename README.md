# eclipse-score .github repository

This repository hosts the start page when you visit the eclipse-score GitHub organization. It contains links to the Eclipse Score website, documentation, and other resources related to the Eclipse Score project.

The Python tool in this repo now acts as a small repo-overview generator: it collects a cached snapshot of organization metadata once, then renders multiple Markdown views from that shared snapshot.
This repository also maintains SCORE-specific governance contracts.

## Development

Use `uv` to create a virtual environment and install dependencies:

```bash
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
uv run generate-repo-overview collect --org-config org_config.toml
```

By default, `collect` now does a cache-aware refresh: it checks fast, high-level
repository state and reuses cached deep details for repositories whose default
branch SHA has not changed. Use this for regular updates.

For volatile repository metrics (open PRs/issues, release counters, and recent
activity), fast mode keeps a per-repository fetch timestamp and refreshes those
values automatically when they are older than 1 hour.

You can tune this freshness window with `REPO_OVERVIEW_VOLATILE_TTL_MINUTES`
(default: `60`).

If you need a full refresh for every repository, run:

```sh
uv run generate-repo-overview collect --clean
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

Run markdown hygiene checks:

```bash
python3 scripts/check_markdown_hygiene.py --root . --include .github --include README.md --include profile
```

Maintenance playbook: [.github/references/docs-maintenance.md](.github/references/docs-maintenance.md)

## Adopting the SCORE Governance Overlay

This repository is a [Copier](https://copier.readthedocs.io/) template. Module repositories apply it once and pull updates with a single command.

### Apply to a new module repo

```bash
# Install Copier once
uv tool install copier

# Apply SCORE overlay into your repo
cd path/to/your-module-repo
copier copy https://github.com/eclipse-score/.github .
```

You will be prompted for:
- Repository name
- Primary language (C++, Rust, Python, Go, Other)
- Build / test / lint commands
- AI assistant instructions filename (default: `copilot-instructions.md` for Copilot, or your runtime's equivalent)

### Pull SCORE governance updates

```bash
# From inside any adopter repo
copier update
```

This re-applies only SCORE-managed files, preserving your repo-local changes.
The `.github/score/.copier-answers.yml` file (written on first `copy`) records the template source and answers, enabling `copier update` to work without re-entering values.

> **Note:** `copier update` requires the template to have at least one git tag.
> Governance updates to this repo must be tagged to be picked up by adopters.

### What gets distributed

| File | Varies per repo? |
|------|-----------------|
| `AGENTS.md` | No — canonical runtime-neutral policy |
| `CLAUDE.md` | No — imports AGENTS.md + Claude-specific notes |
| `.github/<instructions-file>` | No — static SCORE policy |
| `.claude/settings.json` | No — Claude plugin marketplace recommendations |
| `.github/copilot/settings.json` | No — VS Code/Copilot plugin marketplace recommendations |
| `.github/instructions/*.md` | No — coding standards |
| `.github/references/assistant-runtime-alignment.md` | No — multi-runtime alignment guidance |
| `.github/references/*.schema.json` | No — contract schemas |
| `.github/workflows/docs-hygiene.yml` | No — CI checks |
| `scripts/check_markdown_hygiene.py` | No — hygiene tooling |
| `.github/score/repo-manifest.json` | **Yes** — generated from answers |

### Cross-assistant alignment (Copilot, Codex, Claude)

The template follows a single-source model to avoid drift across assistant runtimes:

1. `AGENTS.md` is the canonical, runtime-neutral governance policy.
2. `CLAUDE.md` imports `AGENTS.md` (supported Claude pattern) and carries optional Claude-only notes.
3. `.github/<instructions-file>` is runtime-specific glue for assistants that use a dedicated instructions filename.

This structure aligns with current guidance:
- VS Code agent plugin format supports cross-tool compatibility and shared plugin structures.
- Codex reads layered `AGENTS.md` files directly.
- Claude reads `CLAUDE.md` and supports importing `@AGENTS.md` to avoid duplicated policy.

### What you own in your module repo

- Workflow assets (Spec Kit, OpenSpec, BMAD, or custom) — NOT in this overlay.
- Repo-specific `.github/score/repo-manifest.json` values.
- Any repo-local `.github/instructions/` overrides (stacked on top).

### Why this model

- Maintenance stays in one place — this repo.
- Adopter repos stay current with `copier update`.
- No large agent/prompt/skill catalogs to maintain per-repo.
