"""Resolve pinned dependency revisions against local history clones.

Every comparison runs on a ``repo_cache`` checkout with history, so the
number of GitHub API calls does not grow with the number of pins.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from repo_cache import RepoCacheError, default_cache_directory, sync_default_branch

from generate_repo_overview.console import print_status
from generate_repo_overview.models import (
    DependencyPinKind,
    DependencyResolution,
    dependency_repository,
)

from .git_checkout import git_output
from .registry_metadata import get_bazel_registry_module_sources

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

    from generate_repo_overview.models import RepoEntry
    from generate_repo_overview.org_config import OrgConfig

_COMMIT_HASH = re.compile(r"[0-9a-fA-F]{7,40}")


def map_module_repositories(
    repos: Iterable[RepoEntry],
    configs: Iterable[OrgConfig],
) -> dict[str, str]:
    """Map Bazel module names to their GitHub ``owner/name`` repositories.

    Registry metadata names the source repository explicitly, including for
    modules that are not the root module of their repository. A collected
    repository's own root module name fills the remaining gaps.
    """
    repos = tuple(repo for repo in repos if repo.owner)
    canonical_names = {repo.full_name.casefold(): repo.full_name for repo in repos}
    registered: dict[str, set[str]] = {}
    roots: dict[str, set[str]] = {}
    for registry in dict.fromkeys(config.registry_repo for config in configs):
        for module, sources in get_bazel_registry_module_sources(registry).items():
            registered.setdefault(module, set()).update(
                canonical_names.get(source.casefold(), source.casefold())
                for source in sources
            )
    for repo in repos:
        if repo.content.bazel_module_name:
            roots.setdefault(repo.content.bazel_module_name, set()).add(repo.full_name)
    # With conflicting source identities there is no safe comparison target.
    return {
        module: next(iter(sources))
        for module, sources in sorted((roots | registered).items())
        if len(sources) == 1
    }


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
    revisions: dict[str, set[tuple[DependencyPinKind, str]]] = {}
    for repo in repos:
        for declaration in (
            *repo.content.bazel_deps,
            *repo.volatile.release_bazel_deps,
        ):
            repository = dependency_repository(declaration, module_repositories)
            revision = declaration.pinned_revision
            if repository and revision and repository.casefold() in entries:
                revisions.setdefault(repository.casefold(), set()).add(
                    (declaration.pin_kind, revision)
                )
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
                history=root / entries[key].full_name,
                status_prefix=status_prefix,
            ),
            sorted(revisions),
        )
        return tuple(resolution for result in results for resolution in result)


def _resolve_repository(
    entry: RepoEntry,
    revisions: list[tuple[DependencyPinKind, str]],
    *,
    history: Path,
    status_prefix: str,
) -> list[DependencyResolution]:
    latest_release = entry.volatile.latest_release_version
    if entry.default_branch:
        try:
            sync_default_branch(
                repository=entry.full_name,
                branch=entry.default_branch,
                destination=history,
                history=True,
            )
        except (OSError, RepoCacheError) as exc:
            print_status(
                f"warning: {entry.full_name}: history unavailable; "
                f"dependency pins stay unresolved: {exc}",
                prefix=status_prefix,
            )
        else:
            return _compare_revisions(entry, revisions, history)
    return [
        DependencyResolution(
            entry.full_name, revision, latest_release=latest_release, pin_kind=kind
        )
        for kind, revision in revisions
    ]


def _compare_revisions(
    entry: RepoEntry,
    revisions: list[tuple[DependencyPinKind, str]],
    history: Path,
) -> list[DependencyResolution]:
    default_sha = (
        _commit(history, entry.default_branch_sha)
        if entry.default_branch_sha
        else _ref_commit(history, f"refs/remotes/origin/{entry.default_branch}")
    )
    latest_release = entry.volatile.latest_release_version
    latest_sha = (
        _ref_commit(history, f"refs/tags/{latest_release}") if latest_release else None
    )
    resolutions: list[DependencyResolution] = []
    for kind, revision in revisions:
        sha = _resolve_revision(history, kind, revision)
        ahead_of_default, behind_default = (
            _ahead_behind(history, sha, default_sha)
            if sha and default_sha
            else (None, None)
        )
        behind_latest = (
            _commits_missing_from_release(history, sha, latest_sha)
            if sha and latest_sha
            else None
        )
        resolutions.append(
            DependencyResolution(
                repository=entry.full_name,
                revision=revision,
                resolved_sha=sha,
                latest_release=latest_release,
                behind_latest_release_by=behind_latest,
                ahead_of_default_branch_by=ahead_of_default,
                behind_default_branch_by=behind_default,
                pin_kind=kind,
            )
        )
    return resolutions


def _resolve_revision(
    history: Path, kind: DependencyPinKind, revision: str
) -> str | None:
    if kind is DependencyPinKind.COMMIT:
        return _commit(history, revision) if _COMMIT_HASH.fullmatch(revision) else None
    if kind is DependencyPinKind.BRANCH:
        return _ref_commit(history, f"refs/remotes/origin/{revision}")
    tag = _ref_commit(history, f"refs/tags/{revision}")
    if kind is DependencyPinKind.TAG or revision.startswith("v"):
        return tag
    # Registry versions often omit the tag's "v". If both tags exist and
    # point at different commits, the version alone does not identify a pin.
    prefixed_tag = _ref_commit(history, f"refs/tags/v{revision}")
    if tag and prefixed_tag and tag != prefixed_tag:
        return None
    return tag or prefixed_tag


def _commits_missing_from_release(history: Path, pin: str, release: str) -> int | None:
    ahead, behind = _ahead_behind(history, pin, release)
    if ahead and behind:
        return None
    return behind


def _ref_commit(history: Path, ref: str) -> str | None:
    object_id = git_output(history, "show-ref", "--verify", "--hash", "--", ref)
    return _commit(history, object_id) if object_id else None


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
