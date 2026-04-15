# `generate_repo_overview` Architecture

This package is organized around a single idea:

- collect a normalized snapshot of GitHub organization data
- cache that snapshot on disk
- render multiple Markdown views from the same cached data

This document explains the package structure and cache behavior. It intentionally does not cover CLI usage.

## Module Layout

- `cli.py`
  - Wires the top-level commands together.
  - Decides whether a command should read the cache only, reuse the cache when possible, or perform a live collection.
- `collector.py`
  - Talks to GitHub.
  - Loads repository metadata, custom properties, releases, pull request counts, and content-derived signals.
  - Reads and writes the snapshot cache.
- `models.py`
  - Defines the normalized data structures shared by collection and rendering.
  - The key types are `RepoEntry` and `RepoSnapshot`.
- `profile_readme.py`
  - Renders the organization profile README from normalized repository data.
  - Owns category config parsing, grouping, and README-oriented table rendering.
- `metrics_report.py`
  - Renders the cross-repository metrics report from the same normalized repository data.
- `constants.py`
  - Centralizes default org, cache, and output paths.
- `console.py`
  - Keeps status output formatting in one place.

## Data Flow

The package has three layers:

1. Collection
   - `collector.py` fetches live GitHub data and converts it into `RepoEntry` values.
2. Snapshot
   - The collected repos are stored inside a `RepoSnapshot`.
3. Rendering
   - `profile_readme.py` and `metrics_report.py` render different Markdown views from the same snapshot.

The renderers do not talk to GitHub directly. They only consume normalized data.

## What Is Cached

The main cache file is:

- `profile/cache/repo_overview.json`

That file stores a serialized `RepoSnapshot` containing:

- schema version
- organization name
- generation timestamp
- all normalized repositories

For each repository, the snapshot currently stores:

- repository identity and grouping
  - `name`
  - `description`
  - `category`
  - `subcategory`
- branch identity used for cache reuse
  - `default_branch`
  - `default_branch_sha`
- live repository overview fields
  - `last_push_date`
  - `open_issues`
  - `open_prs`
  - `open_ready_prs`
  - `open_draft_prs`
  - `codeowners`
  - `maintainers_in_bazel_registry`
  - `latest_bazel_registry_version`
  - `latest_release_version`
  - `latest_release_date`
  - `commits_since_latest_release`
  - `stars`
  - `forks`
- content-derived signals
  - `is_bazel_repo`
  - `bazel_version`
  - `has_lint_config`
  - `has_ci`
  - `uses_cicd_daily_workflow`
  - `has_coverage_config`

## What Is Cached Where

There is only one persistent cache file today:

- `profile/cache/repo_overview.json`

There is no separate per-repository cache directory and no checked-out repository mirror.

Instead, the snapshot itself carries enough information to support selective reuse:

- `default_branch_sha` is stored per repository
- on the next live collection, that SHA is compared with the current GitHub default-branch SHA
- if the SHA has not changed, the existing content-derived signals are reused from the snapshot

That means the persistent cache lives in one JSON file, while reuse decisions happen per repository inside the collector.

## What Is Not Cached Separately

The package does not currently maintain separate caches for:

- raw GitHub API responses
- repository trees
- individual file contents
- cloned repositories
- rendered Markdown outputs beyond whatever files the CLI writes

Rendered outputs such as `profile/README.md` and `profile/metrics.md` are products of the snapshot, not part of the snapshot cache itself.

## Cache Semantics By Layer

- Render-only paths read `profile/cache/repo_overview.json` and do not contact GitHub.
- Collection paths always contact GitHub for current repository metadata.
- During collection, some content-derived fields can still be reused from the previous snapshot when the repository content fingerprint (`default_branch_sha`) matches.

This is why cached rendering is fast, while live collection is incremental rather than “download everything again.”

## Why The Package Uses API Access Instead Of Cloning Repositories

The current reports mostly need:

- repository metadata
- custom properties
- release dates
- pull request counts
- file and directory presence checks
- a few small text files such as `.bazelversion`

For that workload, API access is cheaper and simpler than maintaining local clones for every repository.

If the project later needs heavyweight analysis such as line counting, large-scale parsing, or local static analysis across many files, a clone-based backend could be added as a separate collection strategy.
