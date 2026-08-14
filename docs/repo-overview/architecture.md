# Repo Overview Architecture and Data Model

## Architecture

The tool is split into four layers:

1. `org_config.py`
   - Loads organization-specific settings from `org_config.toml`: organization
     name, repository filters, grouping levels, tracked Bazel dependencies,
     workflow signals, reference integration repository, and registry
     repository.
2. `collector/`
   - Uses the GitHub API for organization metadata, custom properties, pull
     requests, issues, releases, and language statistics.
   - Maintains shallow partial Git checkouts for repository trees, branch
     SHAs, configuration files, workflow references, and Sphinx declarations.
   - Derives content signals such as CI, lint, coverage, Bazel version and
     module name, dependencies, and reference-integration usage locally.
   - Loads configured public/private platform repositories and discovers their
     Sphinx feature and module declarations.
   - Writes and reads the JSON snapshot.
3. Renderers
   - `profile_readme.py` renders the organization profile.
   - `metrics_report.py` renders Markdown metrics.
   - `metrics_html.py`, `_html_index.py`, `_html_detail.py`, and
     `_html_common.py` render the HTML dashboard.
   - Renderers consume normalized data and never query GitHub.
4. `cli.py`
   - Orchestrates `collect`, `render-overview`, and `render-details`.

## Data Model

The shared model lives in `models.py`.

- `RepoEntry` contains repository grouping, metrics, and content-derived
  signals.
- `RepoSnapshot` stores:
  - schema version
  - organization name
  - generation timestamp
  - normalized repositories
  - tracked Bazel dependency definitions
  - workflow signal definitions

The snapshot is renderer-agnostic. It stores neutral booleans and strings
rather than Markdown- or HTML-specific values.

## Package Map

- `collector/__init__.py` orchestrates collection and snapshot writes.
- `collector/repo_entry.py` selects the cached, metrics-only, or deep
  per-repository collection path.
- `collector/signal_detection.py` derives repository-local content signals.
- `collector/platform_docs.py` discovers and associates platform Sphinx
  declarations after repository collection.
- `collector/git_checkout.py` owns shallow checkout synchronization and reads.
- `collector/snapshot_io.py` serializes the normalized snapshot.
- `models.py` defines the collection/rendering boundary.
- `profile_readme.py` renders the organization profile.
- `metrics_report.py` renders the Markdown metrics report.
- `metrics_html.py` and `_html_*.py` render the HTML overview and detail pages.
- `cli.py` exposes collection and render commands.

## GitHub API and Git Responsibilities

The collector deliberately uses both transports:

- GitHub API: repository discovery, custom properties, activity metrics,
  release metadata, and language statistics
- Git: default-branch identity, repository trees, configuration contents,
  release `MODULE.bazel`/`.bazelversion`, platform documentation, registry
  metadata, and reference-integration metadata

Content inspection no longer uses GitHub tree or contents endpoints. This
avoids secondary API throttling as the number of inspected files grows.
