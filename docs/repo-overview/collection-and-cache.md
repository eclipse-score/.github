# Repo Overview Collection and Caching

## Snapshot Cache

The default cache file is `.cache/repo_overview.json`.
Repository checkouts share the SCORE `repo_cache` cache:
`${XDG_CACHE_HOME:-~/.cache}/repo-cache/<owner>/<repository>`.

The cache is used in two ways:

- Render commands read the snapshot and do not contact GitHub.
- Collection reuses content-derived signals when a repository's default-branch
  SHA has not changed.

Changing a renderer or template therefore requires no GitHub refresh.

## Incremental Collection

Collection still fetches current high-level repository state, including the
default branch. The shared `repo_cache` package synchronizes each
checkout through the authenticated GitHub CLI and supplies the current commit
SHA. The collector then chooses one of these paths:

- unchanged SHA and fresh volatile metrics: reuse the cached repository entry
- unchanged SHA and stale volatile metrics: refresh activity metrics only
- changed SHA: perform deep content inspection

Platform Sphinx associations are rebuilt from all currently configured
`signals.platform_repos` after these per-repository paths complete. They are
not retained from the previous snapshot, so removing a source or declaration
also removes its associations on the next collection.

Volatile metrics use `volatile_metrics_fetched_at` and are fresh for one hour
by default. Set `REPO_OVERVIEW_VOLATILE_TTL_MINUTES` to change this window.

Use `collect --clean` to delete the snapshot before collection and force a full
content refresh. Existing Git checkouts are retained and updated rather than
cloned again.

## Bazel Lockfile Checks

A changed repository with `MODULE.bazel` and `MODULE.bazel.lock` is checked
with `bazel mod deps --lockfile_mode=error`. The result is a content signal, so
an unchanged repository is not checked again.

Bazel executes code from the repository and inherits the collector's
environment, including the GitHub token. The check therefore runs only for
organizations with `run_repository_tools` enabled. Other repositories report
`skipped`.

Repositories are collected in parallel, but only one lockfile check runs at a
time. Bazel already uses all cores, and concurrent checks would overload small
CI runners. Each checkout has its own Bazel server. The collector shuts it down
after the check. A short idle limit stops servers whose shutdown did not
succeed.

## Transport Split

GitHub API collection is limited to organization and activity metadata:
repository properties, issues, pull requests, releases, and language
statistics.

Git supplies repository content and identity:

- default-branch SHA and last-commit date
- tracked paths and small configuration files
- workflows and CODEOWNERS
- Bazel and Sphinx declarations
- release `MODULE.bazel` and `.bazelversion`

Bazel dependencies are read from `MODULE.bazel` and every module file it
includes. Each `bazel_dep` is stored together with the override Bazel applies
to it, so a `git_override` commit, tag, or branch replaces the declared
version, and `single_version_override` replaces it with the overriding
version.

Checkouts are disposable and start as shallow, single-branch clones. The cache is shared
with other repository tools such as `score-repo-policy-sync` and
`score-repo-cache`. Checkout authentication is handled by `gh`; use
`GITHUB_TOKEN` or `gh auth login` before collecting.

## Dependency Resolution

After all organizations are collected, the snapshot maps Bazel module names
to GitHub repositories for each consuming organization
(`module_repositories`). Each organization uses its configured registry.
A collected repository's root module name fills remaining gaps when it
identifies a single repository. A `git_override` uses its own remote.

Each pinned revision of a collected dependency is then resolved once per
collection into `dependency_resolutions`: the commit it names, how many
commits of the dependency's latest release it lacks, and how far it is ahead
of and behind the dependency's default branch. For a registered module, its
version-specific `source.json` identifies the Git revision. Its latest
non-yanked registry version supplies the release comparison for that module.
For a module absent from the configured registry, an unambiguous matching
tag can resolve a version. Git overrides resolve as a commit, tag, or branch.
Release comparisons use a GitHub release tag only when the repository's
release can be attributed to the module. Unknown pins and unavailable
comparisons are marked on the detail page.

The shared `repo_cache` upgrades a dependency's existing checkout to a blobless
clone with full history when needed. Commit comparisons then run locally,
with no per-pin GitHub API calls. Once upgraded, the checkout keeps its history
for subsequent collections.

For a repository without any commits, GitHub may report a default-branch name
even though that branch cannot be resolved. After a failed checkout, the
collector checks the default branch through the GitHub API before falling back
to an authenticated `ls-remote` check. A missing default branch, or a reachable
remote without references, is collected as an empty repository with neutral
content signals; transport errors and non-empty checkout failures remain
errors.

## Schema Changes

Render commands can read snapshots using schemas 30 through 35. Snapshots
older than schema 35 show consumer data as unavailable. Collection rebuilds
them to refresh dependency declarations, sources, and release comparisons.
