"""Resolve pinned dependency revisions against local history clones.

Every comparison runs on a ``repo_cache`` checkout with history, so the
number of GitHub API calls does not grow with the number of pins.
"""

from __future__ import annotations

import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from functools import cache
from typing import TYPE_CHECKING

from repo_cache import RepoCacheError, default_cache_directory, sync_default_branch

from generate_repo_overview.console import print_status
from generate_repo_overview.models import (
    DependencyPinKind,
    DependencyResolution,
    dependency_repository,
)

from .git_checkout import git_output
from .registry_metadata import (
    RegistryGitSource,
    RegistryModule,
    get_bazel_registry_modules,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping
    from pathlib import Path

    from generate_repo_overview.models import DependencyDeclaration, RepoEntry

    from .registry_metadata import RegistryCheckout

_COMMIT_HASH = re.compile(r"[0-9a-fA-F]{7,40}")


@dataclass(frozen=True, slots=True)
class _Pin:
    resolution: DependencyResolution
    revision: tuple[DependencyPinKind, str] | None
    latest_revision: tuple[DependencyPinKind, str] | None


def collect_dependencies(
    repos: Iterable[RepoEntry],
    registry_checkouts: Mapping[str, RegistryCheckout | None],
    *,
    cache_directory: Path | None = None,
    max_workers: int = 8,
    status_prefix: str = "repo-overview",
) -> tuple[dict[str, Mapping[str, str]], tuple[DependencyResolution, ...]]:
    """Resolve each organization's module sources, then compare pins locally."""
    repos = tuple(repos)
    root = cache_directory or default_cache_directory()
    registries = {
        checkout: get_bazel_registry_modules(checkout.repository, cache_directory=root)
        for checkout in set(registry_checkouts.values())
        if checkout is not None
    }
    registry_by_owner = {
        owner: registries[checkout] if checkout is not None else {}
        for owner, checkout in registry_checkouts.items()
    }
    entries = {entry.full_name.casefold(): entry for entry in repos if entry.owner}
    module_repositories, modules_by_repository = _module_sources(
        entries, registry_by_owner
    )
    pinned = _plan_pins(
        repos,
        module_repositories,
        registry_by_owner,
        registries,
        entries,
        modules_by_repository,
    )
    local = {
        repository: pins for repository, pins in pinned.items() if repository in entries
    }
    external = [
        pin.resolution
        for repository, pins in sorted(pinned.items())
        if repository not in local
        for pin in pins
    ]
    if not local:
        return module_repositories, tuple(external)

    print_status(
        f"Resolving {sum(map(len, local.values()))} dependency pins in {len(local)} repositories",
        prefix=status_prefix,
    )
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(local)))) as pool:
        results = pool.map(
            lambda repository: _resolve_repository(
                entries[repository],
                local[repository],
                history=root / entries[repository].full_name,
                status_prefix=status_prefix,
            ),
            sorted(local),
        )
        return module_repositories, (
            *external,
            *(result for group in results for result in group),
        )


def _module_sources(
    entries: Mapping[str, RepoEntry],
    registries: Mapping[str, Mapping[str, RegistryModule]],
) -> tuple[dict[str, Mapping[str, str]], dict[str, set[str]]]:
    roots: dict[str, set[str]] = defaultdict(set)
    modules_by_repository: dict[str, set[str]] = defaultdict(set)
    for identity, entry in entries.items():
        if module := entry.content.bazel_module_name:
            roots[module].add(identity)
            modules_by_repository[identity].add(module)

    sources: dict[str, Mapping[str, str]] = {}
    for owner, registry in registries.items():
        registered = {
            name: {repo.casefold() for repo in module.repositories}
            for name, module in registry.items()
        }
        for name, repositories in registered.items():
            for repository in repositories:
                modules_by_repository[repository].add(name)
        sources[owner] = {
            name: entries[identity].full_name if identity in entries else identity
            for name, identities in sorted((roots | registered).items())
            if len(identities) == 1
            for identity in identities
        }
    return sources, modules_by_repository


def _plan_pins(
    repos: Iterable[RepoEntry],
    module_repositories: Mapping[str, Mapping[str, str]],
    registry_by_owner: Mapping[str, Mapping[str, RegistryModule]],
    registries: Mapping[RegistryCheckout, Mapping[str, RegistryModule]],
    entries: Mapping[str, RepoEntry],
    modules_by_repository: Mapping[str, set[str]],
) -> dict[str, list[_Pin]]:
    @cache
    def read_source(module: RegistryModule, version: str) -> RegistryGitSource | None:
        return module.git_source(version)

    @cache
    def registry_for_url(url: str) -> Mapping[str, RegistryModule]:
        # An explicit override selects its own registry. Only checkouts of
        # configured registries provide metadata for offline resolution.
        return next(
            (
                modules
                for checkout, modules in registries.items()
                if checkout.matches_url(url)
            ),
            dict[str, RegistryModule](),
        )

    pins: dict[str, list[_Pin]] = defaultdict(list)
    seen: set[tuple[str, str, DependencyPinKind, str, str, str | None]] = set()
    for consumer in repos:
        owner = consumer.owner.casefold()
        default_registry = registry_by_owner.get(owner, {})
        module_sources = module_repositories.get(owner, {})
        for declaration in (
            *consumer.content.bazel_deps,
            *consumer.volatile.release_bazel_deps,
        ):
            revision = declaration.pinned_revision
            if revision is None:
                continue
            override = declaration.registry_override
            registry = (
                default_registry if override is None else registry_for_url(override)
            )
            registry_module = registry.get(declaration.module)
            registry_pin = (
                registry_module
                if declaration.pin_kind is DependencyPinKind.VERSION
                else None
            )
            source = (
                read_source(registry_pin, revision)
                if registry_pin is not None
                else None
            )
            repository = _pin_repository(
                declaration, revision, source, registry_pin, module_sources
            )
            if repository is None:
                continue
            identity = repository.casefold()
            key = (
                owner,
                declaration.module,
                declaration.pin_kind,
                revision,
                identity,
                override,
            )
            if key in seen:
                continue
            seen.add(key)

            latest_version, latest_revision = _latest_module_release(
                declaration,
                registry_module,
                identity,
                entries,
                modules_by_repository,
                read_source,
            )
            revision_to_resolve = (declaration.pin_kind, revision)
            if registry_pin is not None:
                # Registry versions identify packages. Only source.json identifies
                # the Git commits from which these packages were constructed.
                revision_to_resolve = (source.kind, source.revision) if source else None
            pins[identity].append(
                _Pin(
                    DependencyResolution(
                        repository=entries[identity].full_name
                        if identity in entries
                        else repository,
                        revision=revision,
                        latest_release=latest_version,
                        pin_kind=declaration.pin_kind,
                        consumer_org=owner,
                        module=declaration.module,
                        registry_override=override,
                        registry_update_available=(
                            registry_pin.update_available(revision)
                            if registry_pin is not None and identity in entries
                            else None
                        ),
                    ),
                    revision_to_resolve,
                    latest_revision,
                )
            )
    return pins


def _pin_repository(
    declaration: DependencyDeclaration,
    revision: str,
    source: RegistryGitSource | None,
    registry_module: RegistryModule | None,
    default_sources: Mapping[str, str],
) -> str | None:
    if source is not None:
        return source.repository
    if registry_module is not None and not registry_module.has_version(revision):
        # A registry may publish other versions of this module from a fork.
        return None
    if declaration.registry_override is not None and registry_module is not None:
        repositories = {repo.casefold() for repo in registry_module.repositories}
        return next(iter(repositories)) if len(repositories) == 1 else None
    return dependency_repository(declaration, default_sources)


def _latest_module_release(
    declaration: DependencyDeclaration,
    registry_module: RegistryModule | None,
    identity: str,
    entries: Mapping[str, RepoEntry],
    modules_by_repository: Mapping[str, set[str]],
    read_source: Callable[[RegistryModule, str], RegistryGitSource | None],
) -> tuple[str | None, tuple[DependencyPinKind, str] | None]:
    if registry_module is not None:
        version = registry_module.latest_version
        if declaration.pin_kind is DependencyPinKind.VERSION:
            # Registry patches can change the package without changing its
            # source commit. Package freshness is independent of Git ancestry.
            return version, None
        source = read_source(registry_module, version) if version is not None else None
        if source is not None and source.repository.casefold() == identity:
            # Git ancestry cannot account for changes applied by the registry.
            if source.package_modified:
                return version, None
            return version, (source.kind, source.revision)
        known_sources = {repo.casefold() for repo in registry_module.repositories}
        return (
            version if source is None and known_sources == {identity} else None
        ), None

    entry = entries.get(identity)
    if (
        entry is not None
        and entry.content.bazel_module_name == declaration.module
        and modules_by_repository.get(identity) == {declaration.module}
        and (tag := entry.volatile.latest_release_version)
    ):
        return tag, (DependencyPinKind.TAG, tag)
    return None, None


def _resolve_repository(
    entry: RepoEntry,
    pins: list[_Pin],
    *,
    history: Path,
    status_prefix: str,
) -> list[DependencyResolution]:
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
            return _compare_revisions(entry, pins, history)
    return [pin.resolution for pin in pins]


def _compare_revisions(
    entry: RepoEntry, pins: list[_Pin], history: Path
) -> list[DependencyResolution]:
    default_sha = (
        _commit(history, entry.default_branch_sha)
        if entry.default_branch_sha
        else _ref_commit(history, f"refs/remotes/origin/{entry.default_branch}")
    )

    @cache
    def resolve(kind: DependencyPinKind, revision: str) -> str | None:
        return _resolve_revision(history, kind, revision)

    results: list[DependencyResolution] = []
    for pin in pins:
        sha = resolve(*pin.revision) if pin.revision is not None else None
        latest_sha = (
            resolve(*pin.latest_revision) if pin.latest_revision is not None else None
        )
        ahead, behind = (
            _ahead_behind(history, sha, default_sha)
            if sha and default_sha
            else (None, None)
        )
        results.append(
            replace(
                pin.resolution,
                resolved_sha=sha,
                ahead_of_default_branch_by=ahead,
                behind_default_branch_by=behind,
                behind_latest_release_by=(
                    _commits_missing_from_release(history, sha, latest_sha)
                    if sha and latest_sha
                    else None
                ),
            )
        )
    return results


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
