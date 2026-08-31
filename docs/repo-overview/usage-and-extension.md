# Repo Overview Usage and Extension

## Command Surface

The generic entry point is:

```sh
uv run generate-repo-overview <command>
```

Built-in commands:

- `collect --org-config org_config.toml`
  - Synchronizes the snapshot from GitHub.
  - Requires an organization configuration file.
  - `--clean` forces a full refresh.
- `render-overview`
  - Renders the profile README from an existing snapshot.
- `render-details`
  - Renders the HTML dashboard and repository detail pages.
- `fetch-policy-report`
  - Downloads the latest completed policy-sync artifact configured in
    `org_config.toml` using the GitHub CLI. The report is optional and the
    command is best-effort.

The `collect` command performs a GitHub sync. Render commands never contact
GitHub; run `fetch-policy-report` before `render-details` when the policy-sync
dashboard is enabled.

## Setup and Authentication

Install all runtime and development dependencies:

```sh
uv sync --all-groups --frozen
```

Collection reads `GITHUB_TOKEN` and falls back to `gh auth token`. The token
must be able to read every configured organization and platform repository.
The policy report fetch uses `GH_TOKEN`/`GITHUB_TOKEN` through the installed
GitHub CLI (`gh auth login` is sufficient for local use).

## Configuration

`org_config.toml` defines the organization, repository selection and grouping,
tracked Bazel dependencies, workflow signals, shared registry and reference
integration repositories, platform documentation repositories, and optional
policy-sync report metadata. Category order and descriptions for the profile
are stored in
`src/generate_repo_overview/profile_readme_config.toml`.

The policy-sync report artifact contains the evaluation results and policy
metadata, including descriptions. The dashboard renders those descriptions
directly from the report; no policy descriptions are hardcoded in this
repository.

Use `--config /path/to/file.toml` with `render-overview` to select another
profile configuration.

## Cache Controls

`collect` reuses deep repository signals while the default-branch SHA is
unchanged. Volatile metrics expire after 60 minutes by default; set
`REPO_OVERVIEW_VOLATILE_TTL_MINUTES` to another positive number of minutes.

`collect --clean` removes the snapshot before collection and forces content
re-evaluation. It retains the disposable checkout cache. See
[Collection and Caching](collection-and-cache.md) for the complete cache
contract.

## Adding a View

1. Extend `RepoEntry` only when the view needs new normalized data.
2. Add or update a detector in `collector/` when collection must provide new
   data.
3. Add a renderer accepting `RepoSnapshot` or `list[RepoEntry]`.
4. Add a CLI command only if the view needs a separate output surface.

## Adding a Detector

Prefer:

- checks against the synchronized local Git checkout
- targeted reads for small configuration files
- neutral values in the snapshot model

Avoid output-specific markers in the collector. Presentation belongs in the
renderer.
