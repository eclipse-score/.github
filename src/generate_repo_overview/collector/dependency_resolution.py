"""Resolve pinned dependency revisions against local history clones.

Every comparison runs on a treeless ``repo_cache`` history clone, so the
number of GitHub API calls does not grow with the number of pins.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from repo_cache import RepoCacheError, default_cache_directory, sync_history

from generate_repo_overview.console import print_status
from generate_repo_overview.models import DependencyResolution, dependency_repository

from .git_checkout import git_output
from .registry_metadata import get_bazel_registry_repositories_by_module

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

    from generate_repo_overview.models import RepoEntry
    from generate_repo_overview.org_config import OrgConfig

_COMMIT_HASH = re.compile(r"[0-9a-f]{7,40}")


def map_module_repositories(
    repos: Iterable[RepoEntry],
    configs: Iterable[OrgConfig],
) -> dict[str, str]:
    """Map Bazel module names to collected ``owner/name`` repositories.

    Registry metadata names the source repository explicitly, including for
    modules that are not the root module of their repository. A collected
    repository's own root module name fills the remaining gaps.
    """
    repos = tuple(repos)
    mapping: dict[str, str] = {}
    for config in configs:
        if not config.registry_repo:
            continue
        names = {
            repo.name
            for repo in repos
            if repo.owner.casefold() == config.org_name.casefold()
        }
        for module, name in get_bazel_registry_repositories_by_module(
            active_repository_names=names,
            registry_repository=config.registry_repo,
            org_name=config.org_name,
        ).items():
            mapping.setdefault(module, f"{config.org_name}/{name}")
    for repo in repos:
        if repo.content.bazel_module_name:
            mapping.setdefault(repo.content.bazel_module_name, repo.full_name)
    return dict(sorted(mapping.items()))


def resolve_dependencies(
    repos: Iterable[RepoEntry],
    module_repositories: Mapping[str, str],
    *,
    cache_directory: Path | None = None,
    max_workers: int = 8,
    status_prefix: str = "repo-overview",
) -> tuple[DependencyResolution, ...]:
    """Compare every pinned revision of a collected repository with its history.

    Only dependencies on collected repositories are resolved: the default
    branch and latest release used for comparison come from their entries.
    """
    repos = tuple(repos)
    entries = {repo.full_name.casefold(): repo for repo in repos}
    revisions: dict[str, set[str]] = {}
    for repo in repos:
        for declaration in (
            *repo.content.bazel_deps,
            *repo.volatile.release_bazel_deps,
        ):
            repository = dependency_repository(declaration, module_repositories)
            revision = declaration.pinned_revision
            if repository and revision and repository.casefold() in entries:
                revisions.setdefault(repository.casefold(), set()).add(revision)
    if not revisions:
        return ()

    root = cache_directory or default_cache_directory()
    print_status(
        f"Resolving {sum(map(len, revisions.values()))} dependency pins "
        f"in {len(revisions)} repositories",
        prefix=status_prefix,
    )
    with ThreadPoolExecutor(
        max_workers=max(1, min(max_workers, len(revisions)))
    ) as pool:
        results = pool.map(
            lambda key: _resolve_repository(
                entries[key],
                sorted(revisions[key]),
                history=root / f"{entries[key].full_name}.git",
                status_prefix=status_prefix,
            ),
            sorted(revisions),
        )
        return tuple(resolution for result in results for resolution in result)


def _resolve_repository(
    entry: RepoEntry,
    revisions: list[str],
    *,
    history: Path,
    status_prefix: str,
) -> list[DependencyResolution]:
    try:
        sync_history(repository=entry.full_name, destination=history)
    except (OSError, RepoCacheError) as exc:
        print_status(
            f"warning: {entry.full_name}: history unavailable; "
            f"dependency pins stay unresolved: {exc}",
            prefix=status_prefix,
        )
        return [
            DependencyResolution(entry.full_name, revision) for revision in revisions
        ]

    default_sha = (
        _commit(history, f"refs/heads/{entry.default_branch}")
        if entry.default_branch
        else None
    )
    latest_release = entry.volatile.latest_release_version
    latest_sha = (
        _commit(history, f"refs/tags/{latest_release}") if latest_release else None
    )
    resolutions: list[DependencyResolution] = []
    for revision in revisions:
        sha = _resolve_revision(history, revision)
        ahead_of_default, behind_default = (
            _ahead_behind(history, sha, default_sha)
            if sha and default_sha
            else (None, None)
        )
        _, behind_latest = (
            _ahead_behind(history, sha, latest_sha)
            if sha and latest_sha
            else (None, None)
        )
        resolutions.append(
            DependencyResolution(
                repository=entry.full_name,
                revision=revision,
                resolved_sha=sha,
                latest_release=latest_release if latest_sha else None,
                behind_latest_release_by=behind_latest,
                ahead_of_default_branch_by=ahead_of_default,
                behind_default_branch_by=behind_default,
            )
        )
    return resolutions


def _resolve_revision(history: Path, revision: str) -> str | None:
    """Resolve a commit, tag, branch, or release version to a commit hash."""
    # Registry versions usually omit the tag's "v" prefix.
    candidates = [
        f"refs/tags/{revision}",
        f"refs/tags/v{revision}",
        f"refs/heads/{revision}",
    ]
    if _COMMIT_HASH.fullmatch(revision):
        candidates.insert(0, revision)
    for candidate in candidates:
        sha = _commit(history, candidate)
        if sha is not None:
            return sha
    return None


def _commit(history: Path, ref: str) -> str | None:
    return git_output(
        history,
        "rev-parse",
        "--verify",
        "--quiet",
        "--end-of-options",
        f"{ref}^{{commit}}",
    )


def _ahead_behind(
    history: Path, pin: str, target: str
) -> tuple[int | None, int | None]:
    """Count commits only in *pin* and only in *target*.

    Without a common ancestor the counts would span both entire histories,
    so unrelated revisions stay uncomparable.
    """
    if git_output(history, "merge-base", pin, target) is None:
        return None, None
    counts = git_output(
        history, "rev-list", "--left-right", "--count", f"{pin}...{target}"
    )
    if counts is None:
        return None, None
    ahead, behind = counts.split()
    return int(ahead), int(behind)
