# Repo Overview Collection and Caching

## Snapshot Cache

The default cache file is `.cache/repo_overview.json`.
Repository checkouts share the SCORE repository-policy cache:
`${XDG_CACHE_HOME:-~/.cache}/repo-cache/<owner>/<repository>`.

The cache is used in two ways:

- Render commands read the snapshot and do not contact GitHub.
- Collection reuses content-derived signals when a repository's default-branch
  SHA has not changed.

Changing a renderer or template therefore requires no GitHub refresh.

## Incremental Collection

Collection still fetches current high-level repository state, including the
default branch. Git synchronizes each shallow partial checkout and supplies the
current commit SHA. The collector then chooses one of these paths:

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

Checkouts are disposable, shallow, single-branch partial clones. The generic
cache is shared with other repository tools such as `score-repo-policy-sync`.
Authentication is passed through a transient Git HTTP header and is not written
into the remote URL.

For a repository without any commits, GitHub may report a default-branch name
even though that branch cannot be resolved. After a failed checkout, the
collector checks the default branch through the GitHub API before falling back
to an authenticated `ls-remote` check. A missing default branch, or a reachable
remote without references, is collected as an empty repository with neutral
content signals; transport errors and non-empty checkout failures remain
errors.

## Schema Changes

The loader accepts only the current snapshot schema version. An incompatible
snapshot is ignored and replaced by a fresh collection. This prevents fields
added by new detectors or views from receiving stale defaults indefinitely.
