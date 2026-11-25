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
    `org_config.toml` using the GitHub CLI. Invoking this command requires a
    report configuration and a valid report; otherwise it fails so a publishing
    workflow can keep its last deployed view.

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
The shared `repo_cache` dependency uses the authenticated `gh` CLI for Git
checkout synchronization; a custom `--token-env` value is forwarded to it.
The policy report fetch uses `GH_TOKEN`/`GITHUB_TOKEN` through the installed
GitHub CLI (`gh auth login` is sufficient for local use).

## Configuration

`org_config.toml` defines the organizations with their repository selection,
grouping, registry, and reference integration repositories; tracked Bazel
dependencies, workflow signals, and platform documentation repositories; and
optional policy-sync report metadata. Category order and descriptions for the profile
are stored in
`src/generate_repo_overview/profile_readme_config.toml`.

The policy-sync report artifact contains the evaluation results and policy
metadata, including descriptions. The dashboard renders those descriptions
directly from the report; no policy descriptions are hardcoded in this
repository.

Use `--config /path/to/file.toml` with `render-overview` to select another
profile configuration.

The organization config rejects settings it does not know, so a misspelled
key fails the command instead of silently using its default.

### Organizations

Each GitHub organization has its own `[organizations.<name>]` table. An
organization uses only the settings of its own table; nothing is inherited
from another organization. Omit `registry_repo`, `reference_integration_repo`,
or `grouping_levels` when the organization has none.

```toml
[organizations.example-platform]
run_repository_tools = true
repo_include_patterns = ["platform-*"]
registry_repo = "example-platform/bazel-registry"
reference_integration_repo = "example-platform/integration"
grouping_levels = [{ property = "category", default = "Uncategorized" }]

[organizations.example-tools]
run_repository_tools = false
repo_include_patterns = ["compiler", "build-*"]
grouping_levels = [{ property = "team", default = "Tooling" }]
```

An omitted or empty `repo_include_patterns` includes all active repositories of
the organization. Tracked dependencies and workflow signals are configured per
organization as well, so each organization's sections show only its own
columns; list a shared workflow or dependency in every organization that uses
it. Platform documentation sources in `[signals]` apply to all organizations.

`run_repository_tools` is required. It decides whether collection may start
tools inside repository checkouts. Such tools execute code from the repository
and inherit the collector's environment, so that code could read and leak the
GitHub token. Set it to `true` only for organizations whose default branches
are trusted with that token. Collection currently starts no such tools, so the
setting has no effect yet.

The dashboard lists each organization's groups together in the combined view.
The **Organization** filter in the filter bar scopes repository lists and the
overview summary to one organization. The selected organization can be bookmarked with
the tab and other filters.

The first table is the primary organization. The snapshot and cache
distinguish repositories by `owner/repo`. Primary organization detail pages
are at `<repo>/`. Additional organizations use `@orgs/<owner>/<repo>/`.
Every box on a detail page has an anchor, such as `<repo>/#used-by`; its title
links to it.

Policy report entries with short repository names use the primary organization
by default. Set `repository_owner` in `[policy_report]` when those names refer
to another organization. Entries that include `owner/repo` use their own owner.
The filters scope the policy matrix rows. Policy totals always describe the
entire report.

### Tracked Workflows

Configure one `[[organizations.<name>.workflow_signals]]` entry per reusable
workflow:

```toml
[[organizations.example-platform.workflow_signals]]
label = "Daily"
reference = "eclipse-score/cicd-workflows/.github/workflows/daily.yml@"
```

The **Workflows** tab appears only when at least one workflow is configured.
It shows sections only for organizations with configured workflows.
Each column shows the distinct tags, branches, or commit pins used by a repository,
linked to the reusable workflow source. Full commit hashes are shortened for display;
the full reference remains available on hover. Multiple pins are shown together,
and `—` means the repository does not call that workflow.

Collection parses job-level `uses` entries in `.github/workflows/*.yml` and
`*.yaml`. Comments, shell snippets, step-level actions, and calls nested inside
external workflows do not count as direct adoption. Invalid YAML files are skipped.
Keep the trailing `@` in the configured prefix to match any version of one workflow.
Workflow pins also appear on repository detail pages.

During collection, pins are resolved against tags in the workflow source
repository. An exact version tag replaces the abbreviated hash in the display;
the link still targets the original pin, which remains visible on hover.
Workflow-specific tags such as `on-pr/v1.2.3` take precedence over global version
tags at the same commit; tags for other workflows are ignored. Version tags use
green labels. A tag at the latest release omits the redundant comparison;
older tags keep their comparison. Workflow-specific tags such as `on-pr/v0.0.0`
are not compared with releases from a different tag series, such as `v0.0.3`.

Next to each pin, `vs <release>` compares it with the latest published release
of the **workflow source repository**. As in the Versions tab, `↑N` means the
pin is N commits ahead, `↓N` means it is N commits behind, and `=` means both
point to the same commit. Diverged histories show both arrows. `?` means the
comparison was unavailable. Without a published release, only the pin or its
matching version tag is shown; unresolved pins retain their original display.

Source tags, releases, and branch pins are refreshed on every collection,
including when consumer repositories reuse cached content. Each source
repository and distinct pin is queried once per collection, so consumers
sharing pins do not multiply the API requests. Rendering remains offline.

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

### Dependency Freshness

Repository detail pages list the direct Bazel dependencies declared on the default
branch and in the latest release, with root module overrides applied. Bazel may
select a different version when it resolves the full dependency graph.

- The **release** badge compares a registry pin with the latest non-yanked module
  version. Git pins are compared with an identifiable release of that module.
  Tracked dependency summaries use the same release status.
- The **default branch** badge shows how many commits the pin is behind the
  dependency's default branch and links to the comparison. A pin that has
  diverged from the default branch is marked as such.

An explicit registry URL in a `single_version_override` can be resolved when
it points to the root of a configured GitHub registry's cached default branch.
Other registry URLs leave the source unknown.

The **Used by** section lists collected repositories that declare a direct
dependency, along with their declared pins, grouped by their top-level
category.
Freshness and consumers are only known for repositories in the overview;
external modules such as `rules_python` show their version only, and pins
without a matching commit, tag, or branch are marked as unresolved.
