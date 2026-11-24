from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from functools import partial
from time import monotonic
from typing import TYPE_CHECKING, Any, Protocol, cast

from tqdm import tqdm

from generate_repo_overview.console import print_status
from generate_repo_overview.constants import (
    DEFAULT_CACHE,
    DEFAULT_REPOSITORY_CHECKOUTS,
    DEFAULT_TOKEN_ENV,
)
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    CustomPropertyValue,
    RepoEntry,
    RepoSnapshot,
)
from generate_repo_overview.org_config import OrgConfig

from . import (
    dependency_resolution,
    platform_docs,
    reference_integration,
    registry_metadata,
    repo_entry,
    traceability,
    workflow_versions,
)
from .git_checkout import sync_repository_checkout
from .registry_metadata import RegistrySignalsPayload
from .snapshot_io import load_snapshot, load_snapshot_if_present, write_snapshot

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from github import Github


class OrganizationLike(Protocol):
    @property
    def login(self) -> str: ...

    requester: Any


class GitHubClientLike(Protocol):
    def get_rate_limit(self) -> object: ...


class RepositoryResolverLike(Protocol):
    def get_repo(self, full_name_or_id: str) -> object: ...


@dataclass(frozen=True, slots=True)
class ActiveRepositoryData:
    repository: object
    custom_properties: dict[str, CustomPropertyValue]


DEFAULT_MAX_COLLECTION_WORKERS = 8

__all__ = [
    "DEFAULT_MAX_COLLECTION_WORKERS",
    "SNAPSHOT_SCHEMA_VERSION",
    "ActiveRepositoryData",
    "RegistrySignalsPayload",
    "collect_snapshot",
    "ensure_snapshot",
    "fetch_active_repositories",
    "fetch_active_repositories_via_rest",
    "fetch_repositories",
    "fetch_repository_descriptions",
    "get_gh_auth_token",
    "load_snapshot",
    "load_snapshot_if_present",
    "paginate_github_rest_list",
    "parse_repository_custom_properties",
    "resolve_github_token",
    "resolve_max_collection_workers",
    "write_snapshot",
]


def resolve_github_token(token_env: str = DEFAULT_TOKEN_ENV) -> str | None:
    token = os.getenv(token_env)
    if token:
        return token
    return get_gh_auth_token()


def get_gh_auth_token() -> str | None:
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    token = result.stdout.strip()
    return token or None


def ensure_snapshot(
    *,
    config: OrgConfig,
    cache_path: Path = DEFAULT_CACHE,
    token_env: str = DEFAULT_TOKEN_ENV,
    refresh: bool = False,
    status_prefix: str = "repo-overview",
) -> RepoSnapshot:
    if not refresh:
        cached_snapshot = load_snapshot_if_present(cache_path)
        if cached_snapshot is not None:
            print_status(
                f"Loading cached snapshot from {cache_path}",
                prefix=status_prefix,
            )
            return cached_snapshot

    return collect_snapshot(
        config=config,
        token_env=token_env,
        cache_path=cache_path,
        status_prefix=status_prefix,
    )


def collect_snapshot(
    *,
    config: OrgConfig,
    token_env: str = DEFAULT_TOKEN_ENV,
    cache_path: Path | None = DEFAULT_CACHE,
    status_prefix: str = "repo-overview",
) -> RepoSnapshot:
    """Collect a fresh snapshot from GitHub, reusing unchanged repository data from cache.

    Loads the existing snapshot from *cache_path* for incremental reuse.
    Invalidates the content cache when workflow signal definitions in
    *config* differ from the cached snapshot.
    Delete the cache file before calling to force a full refresh (see ``--clean``).
    """
    try:
        from github import Auth, Github
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing PyGithub. Install project dependencies before running the generator."
        ) from exc

    org_name = config.org_name

    token = resolve_github_token(token_env)
    if not token:
        message = f"Missing GitHub token. Set {token_env} or authenticate with `gh auth login`."
        raise SystemExit(message)

    existing_snapshot = (
        load_snapshot_if_present(cache_path) if cache_path is not None else None
    )

    print_status(f"Connecting to GitHub organization {org_name}", prefix=status_prefix)
    github = Github(auth=Auth.Token(token), lazy=True)
    print_rest_api_rate_limit(
        github,
        when="before collection",
        status_prefix=status_prefix,
    )
    # repo_cache starts gh subprocesses for checkout synchronization.  GH_TOKEN
    # gives those subprocesses the same credential used by PyGithub, including
    # when the caller selected a custom --token-env variable.
    previous_gh_token = os.environ.get("GH_TOKEN")
    os.environ["GH_TOKEN"] = token
    try:
        configs = config.collection_configs()
        repos: list[RepoEntry] = []
        registries: dict[str, registry_metadata.RegistryCheckout | None] = {}
        for org_config in configs:
            org_repos, registry = _collect_organization(
                github,
                config=org_config,
                existing_snapshot=existing_snapshot,
                token=token,
                status_prefix=status_prefix,
            )
            repos.extend(org_repos)
            registries[org_config.org_name.casefold()] = registry
        repos = enrich_repositories_with_platform_docs(
            repos,
            github=github,
            platform_repos=config.platform_repos,
            status_prefix=status_prefix,
        )

        module_repositories, dependency_resolutions = (
            dependency_resolution.collect_dependencies(
                repos,
                registries,
                max_workers=resolve_max_collection_workers(),
                status_prefix=status_prefix,
            )
        )
        snapshot = RepoSnapshot(
            schema_version=SNAPSHOT_SCHEMA_VERSION,
            org_name=org_name,
            additional_org_names=tuple(c.org_name for c in configs[1:]),
            generated_at=datetime.now(UTC).isoformat(),
            repos=tuple(repos),
            tracked_deps=config.tracked_deps,
            workflow_signals=config.workflow_signals,
            workflow_ref_resolutions=workflow_versions.fetch_workflow_ref_resolutions(
                repos, github=github, status_prefix=status_prefix
            ),
            module_repositories=module_repositories,
            dependency_resolutions=dependency_resolutions,
        )
        if cache_path is not None:
            write_snapshot(snapshot, cache_path)
            print_status(f"Wrote snapshot to {cache_path}", prefix=status_prefix)
        return snapshot
    finally:
        if previous_gh_token is None:
            os.environ.pop("GH_TOKEN", None)
        else:
            os.environ["GH_TOKEN"] = previous_gh_token
        print_rest_api_rate_limit(
            github,
            when="after collection",
            status_prefix=status_prefix,
        )


def _collect_organization(
    github: Github,
    *,
    config: OrgConfig,
    existing_snapshot: RepoSnapshot | None,
    token: str,
    status_prefix: str,
) -> tuple[list[RepoEntry], registry_metadata.RegistryCheckout | None]:
    print_status(f"Collecting repositories in {config.org_name}", prefix=status_prefix)
    organization = github.get_organization(config.org_name)
    registry_repository = None
    registry = None
    if config.registry_repo:
        try:
            candidate = github.get_repo(config.registry_repo)
            # The lazy GitHub object starts with the requested name. Reading
            # the branch loads the API response and its canonical full name.
            default_branch = candidate.default_branch
            registry = registry_metadata.RegistryCheckout(
                candidate.full_name, default_branch
            )
            registry_repository = candidate
        except Exception as exc:
            print_status(
                f"Could not resolve registry repo {config.registry_repo}: {exc}",
                prefix=status_prefix,
            )

    repos = fetch_repositories(
        organization,
        existing_snapshot=existing_snapshot,
        github_token=token,
        status_prefix=status_prefix,
        config=config,
        registry_repository=registry_repository,
        github=github,
    )
    trace_by_repo = traceability.fetch_all_traceability_metrics(
        config.org_name,
        repos,
        tracked_deps=config.tracked_deps,
        status_prefix=status_prefix,
    )
    return (
        [
            replace(entry, traceability=trace_by_repo[entry.name])
            if entry.name in trace_by_repo
            else entry
            for entry in repos
        ],
        registry,
    )


def enrich_repositories_with_platform_docs(
    repos: list[RepoEntry],
    *,
    github: RepositoryResolverLike,
    platform_repos: tuple[str, ...],
    status_prefix: str,
) -> list[RepoEntry]:
    enriched = [
        replace(
            entry,
            content=replace(
                entry.content,
                sphinx_features=(),
                sphinx_modules=(),
            ),
        )
        for entry in repos
    ]
    for full_name in platform_repos:
        print_status(
            f"Loading Sphinx module metadata from {full_name}",
            prefix=status_prefix,
        )
        repository = github.get_repo(full_name)
        default_branch = cast("str | None", getattr(repository, "default_branch", None))
        if default_branch is None:
            raise RuntimeError(
                f"Configured platform repository {full_name} has no default branch."
            )
        checkout_path = sync_repository_checkout(
            repository=full_name,
            default_branch=default_branch,
            checkout_path=DEFAULT_REPOSITORY_CHECKOUTS / full_name,
        )
        if checkout_path is None:
            raise RuntimeError(
                f"Could not synchronize configured platform repository {full_name}."
            )
        enriched = platform_docs.enrich_repositories_from_platform_docs(
            enriched,
            checkout_path=checkout_path,
            source_repo=full_name,
        )
    return enriched


def print_rest_api_rate_limit(
    github_client: GitHubClientLike,
    *,
    when: str,
    status_prefix: str,
) -> None:
    try:
        rate_limit = github_client.get_rate_limit()
        resources = getattr(rate_limit, "resources", None)
        core_rate_limit = getattr(resources, "core", None)
        if core_rate_limit is None:
            core_rate_limit = getattr(rate_limit, "core", None)
        if core_rate_limit is None:
            raise AttributeError("Missing core rate limit data.")
    except Exception as exc:
        print_status(
            f"GitHub REST API rate limit {when}: unavailable ({exc})",
            prefix=status_prefix,
        )
        return

    reset_at = getattr(core_rate_limit, "reset", None)
    if isinstance(reset_at, datetime):
        reset_display = reset_at.isoformat()
    else:
        reset_display = "unknown"

    print_status(
        "GitHub REST API rate limit "
        f"{when}: remaining {getattr(core_rate_limit, 'remaining', 'unknown')}/"
        f"{getattr(core_rate_limit, 'limit', 'unknown')}, "
        f"used {getattr(core_rate_limit, 'used', 'unknown')}, "
        f"resets at {reset_display}",
        prefix=status_prefix,
    )


def fetch_repositories(
    organization: OrganizationLike,
    existing_snapshot: RepoSnapshot | None = None,
    *,
    github_token: str | None = None,
    status_prefix: str = "repo-overview",
    config: OrgConfig | None = None,
    registry_repository: object | None = None,
    github: RepositoryResolverLike | None = None,
) -> list[RepoEntry]:
    """Fetch and collect all repository entries for an organization.

    Resolves registry metadata, reference integration dependencies and
    workflow signals, then dispatches parallel per-repo collection.
    Reuses cached content signals when the default-branch SHA is unchanged
    and workflow signal definitions have not changed since the cached snapshot.
    """
    if config is None:
        config = OrgConfig(org_name=organization.login)

    print_status("Loading active repositories", prefix=status_prefix)
    active_repositories = fetch_active_repositories(organization, config=config)
    print_status(
        f"Found {len(active_repositories)} active repositories",
        prefix=status_prefix,
    )
    print_status(
        "Extracting repository custom properties from repo payloads",
        prefix=status_prefix,
    )
    repositories_with_custom_properties = sum(
        1
        for repository_data in active_repositories.values()
        if repository_data.custom_properties
    )
    print_status(
        "Extracted custom properties for "
        f"{repositories_with_custom_properties} repositories",
        prefix=status_prefix,
    )
    resolved_registry_repository = cast(
        "str | None", getattr(registry_repository, "full_name", None)
    )
    registry_repository_name = resolved_registry_repository or config.registry_repo

    bazel_registry_metadata_by_repo: dict[
        str, registry_metadata.RegistrySignalsPayload
    ] = {}
    if config.registry_repo:
        print_status(
            f"Loading maintainers in {config.registry_repo}",
            prefix=status_prefix,
        )
        bazel_registry_metadata_by_repo = (
            registry_metadata.fetch_bazel_registry_metadata_by_repo(
                bazel_registry_repository=registry_repository,
                active_repository_names=set(active_repositories),
                org_name=config.org_name,
            )
        )
        print_status(
            f"Loaded {config.registry_repo} metadata for "
            f"{len(bazel_registry_metadata_by_repo)} active repositories",
            prefix=status_prefix,
        )

    reference_integration_repository_names, reference_integration_pins = (
        _collect_reference_integration(
            config, active_repositories, registry_repository_name, github, status_prefix
        )
    )

    # Entries of the previous snapshot stand in for repositories that fail.
    earlier_by_full_name: dict[str, RepoEntry] = {}
    cached_by_full_name: dict[str, RepoEntry] = {}
    if existing_snapshot is not None:
        earlier_by_full_name = {
            f"{repo.owner or existing_snapshot.org_name}/{repo.name}".casefold(): repo
            for repo in existing_snapshot.repos
        }
        if config.workflow_signals == existing_snapshot.workflow_signals:
            cached_by_full_name = earlier_by_full_name
        else:
            print_status(
                "Workflow signal definitions changed — ignoring content cache",
                prefix=status_prefix,
            )
    sorted_repositories = sorted(
        active_repositories.items(),
        key=lambda item: item[0].casefold(),
    )

    total_repositories = len(sorted_repositories)
    if total_repositories == 0:
        return []

    max_workers = min(resolve_max_collection_workers(), total_repositories)
    print_status(
        f"Collecting repository details with up to {max_workers} parallel workers",
        prefix=status_prefix,
    )

    repos_by_index: dict[int, RepoEntry] = {}
    failed_repository_names: list[str] = []
    finished_repositories = 0
    with (
        ThreadPoolExecutor(max_workers=max_workers) as executor,
        tqdm(
            total=total_repositories,
            desc="Finished",
            unit="repo",
            file=sys.stderr,
            disable=not sys.stderr.isatty(),
        ) as progress,
    ):
        futures: dict[Future[RepoEntry], tuple[int, str]] = {}
        for index, (repository_name, repository_data) in enumerate(
            sorted_repositories,
            start=1,
        ):
            cached_entry = cached_by_full_name.get(
                f"{config.org_name}/{repository_name}".casefold()
            )
            collect_entry = partial(
                repo_entry.collect_repository_entry,
                repository_name=repository_name,
                repository=repository_data.repository,
                custom_properties=repository_data.custom_properties,
                grouping_levels=config.grouping_levels,
                bazel_registry_metadata=bazel_registry_metadata_by_repo.get(
                    repository_name
                ),
                cached_entry=cached_entry,
                referenced_by_reference_integration=(
                    repository_name in reference_integration_repository_names
                ),
                workflow_signals=config.workflow_signals,
                github_token=github_token,
                run_repository_tools=config.run_repository_tools,
            )
            future = executor.submit(
                _collect_entry_with_reference_refs,
                collect_entry,
                repository_data.repository,
                reference_integration_pins.get(repository_name),
            )
            futures[future] = (index, repository_name)

        for future in as_completed(futures):
            index, repository_name = futures[future]
            progress.update(1)
            progress.set_postfix_str(repository_name)
            finished_repositories += 1
            try:
                entry = future.result()
            except Exception as exc:
                failed_repository_names.append(repository_name)
                cached_entry = _earlier_result_for_failed_repository(
                    repository_name,
                    exc,
                    earlier_by_full_name.get(
                        f"{config.org_name}/{repository_name}".casefold()
                    ),
                    status_prefix,
                )
                if cached_entry is None:
                    continue
                entry = cached_entry
            repos_by_index[index] = replace(entry, owner=config.org_name)
            print_status(
                f"Finished {finished_repositories}/{total_repositories} repositories ({repository_name})",
                prefix=status_prefix,
            )

    _report_failed_repositories(
        failed_repository_names, total_repositories, config.org_name, status_prefix
    )
    return [
        repos_by_index[index]
        for index in range(1, total_repositories + 1)
        if index in repos_by_index
    ]


def _earlier_result_for_failed_repository(
    repository_name: str,
    error: Exception,
    cached_entry: RepoEntry | None,
    status_prefix: str,
) -> RepoEntry | None:
    """Keep the dashboard refreshing when one repository cannot be collected."""
    if cached_entry is None:
        print_status(
            f"warning: {repository_name}: collection failed and no earlier "
            f"result exists; leaving it out ({error})",
            prefix=status_prefix,
        )
        return None
    print_status(
        f"warning: {repository_name}: collection failed; keeping the result "
        f"of an earlier collection ({error})",
        prefix=status_prefix,
    )
    return cached_entry


def _report_failed_repositories(
    failed_repository_names: list[str],
    total_repositories: int,
    org_name: str,
    status_prefix: str,
) -> None:
    failed = len(failed_repository_names)
    if failed > 1 and failed > total_repositories / 2:
        # So many failures are not caused by single repositories. Publishing
        # earlier results would hide a broken token, an exhausted rate limit,
        # or an unreachable GitHub.
        raise RuntimeError(
            f"Collection failed for {failed} of {total_repositories} "
            f"repositories in {org_name}."
        )
    if failed_repository_names:
        print_status(
            f"warning: collection failed for {len(failed_repository_names)} of "
            f"{total_repositories} repositories in {org_name}: "
            + ", ".join(sorted(failed_repository_names, key=str.casefold)),
            prefix=status_prefix,
        )


def _collect_reference_integration(
    config: OrgConfig,
    active_repositories: dict[str, ActiveRepositoryData],
    registry_repository: str,
    github: RepositoryResolverLike | None,
    status_prefix: str,
) -> tuple[set[str], dict[str, reference_integration.KnownGoodPin]]:
    from github import GithubException

    if not config.reference_integration_repo:
        return set(), {}

    print_status(
        f"Loading {config.reference_integration_repo} Bazel dependencies",
        prefix=status_prefix,
    )
    reference_owner, reference_name = config.reference_integration_repo.split("/", 1)
    reference_data = (
        active_repositories.get(reference_name)
        if reference_owner.casefold() == config.org_name.casefold()
        else None
    )
    reference_repository = reference_data.repository if reference_data else None
    try:
        if reference_data is None and github is not None:
            reference_repository = github.get_repo(config.reference_integration_repo)
        repository_names = (
            reference_integration.fetch_reference_integration_repository_names(
                reference_integration_repository=reference_repository,
                active_repository_names=set(active_repositories),
                registry_repository=registry_repository,
                org_name=config.org_name,
            )
        )
        pins = reference_integration.fetch_reference_integration_pins(
            reference_integration_repository=reference_repository,
            active_repository_names=set(active_repositories),
            org_name=config.org_name,
        )
    except GithubException as exc:
        if exc.status != 404:
            raise
        print_status(
            f"Reference integration repository {config.reference_integration_repo} is unavailable",
            prefix=status_prefix,
        )
        return set(), {}

    repository_names.update(pins)
    print_status(
        f"Loaded {config.reference_integration_repo} Bazel dependencies for "
        f"{len(repository_names)} active repositories",
        prefix=status_prefix,
    )
    return repository_names, pins


def _collect_entry_with_reference_refs(
    collect_entry: Callable[[], RepoEntry],
    repository: object,
    pin: reference_integration.KnownGoodPin | None,
) -> RepoEntry:
    """Collect a repository and compare its release and integration refs in a worker."""
    started = monotonic()
    entry = collect_entry()
    print_status(f"{entry.name}: comparing release and integration refs")
    raw_default_branch = getattr(repository, "default_branch", None)
    main_branch = (
        raw_default_branch.strip()
        if isinstance(raw_default_branch, str) and raw_default_branch.strip()
        else (pin.branch if pin is not None else "main")
    )
    release = entry.volatile.latest_release_version
    release_ahead = entry.volatile.latest_release_ahead_of_default_branch_by
    branch_ahead = entry.volatile.default_branch_ahead_of_latest_release_by
    if release and (release_ahead is None or branch_ahead is None):
        release_comparison = reference_integration.compare_git_refs(
            repository,
            left_ref=main_branch,
            right_ref=release,
        )
        if release_comparison is not None:
            release_ahead = release_comparison.right_ahead_by
            branch_ahead = release_comparison.left_ahead_by
    resolved_pin_hash = (
        reference_integration.resolve_reference_integration_pin(repository, pin)
        if pin is not None
        else None
    )
    pin_comparison = (
        reference_integration.compare_git_refs(
            repository,
            left_ref=main_branch,
            right_ref=resolved_pin_hash,
        )
        if resolved_pin_hash is not None
        else None
    )
    content = replace(
        entry.content,
        reference_integration_release_ahead_of_main_by=release_ahead,
        reference_integration_main_ahead_of_release_by=branch_ahead,
        reference_integration_pin_ahead_of_main_by=(
            pin_comparison.right_ahead_by if pin_comparison is not None else None
        ),
        reference_integration_main_ahead_of_pin_by=(
            pin_comparison.left_ahead_by if pin_comparison is not None else None
        ),
        reference_integration_module=pin.module if pin is not None else None,
        reference_integration_group=pin.group if pin is not None else None,
        reference_integration_branch=main_branch if pin is not None else None,
        reference_integration_version=pin.version if pin is not None else None,
        reference_integration_hash=pin.commit_hash if pin is not None else None,
        reference_integration_resolved_hash=resolved_pin_hash,
    )
    print_status(f"{entry.name}: completed collection in {monotonic() - started:.1f}s")
    return replace(entry, content=content)


def resolve_max_collection_workers() -> int:
    raw_value = os.getenv("REPO_OVERVIEW_MAX_WORKERS", "").strip()
    if raw_value:
        try:
            parsed = int(raw_value)
        except ValueError:
            return DEFAULT_MAX_COLLECTION_WORKERS
        if parsed > 0:
            return parsed
    return DEFAULT_MAX_COLLECTION_WORKERS


def fetch_active_repositories(
    organization: OrganizationLike,
    *,
    config: OrgConfig | None = None,
) -> dict[str, ActiveRepositoryData]:
    return fetch_active_repositories_via_rest(
        requester=organization.requester,
        org_login=organization.login,
        config=config,
    )


def fetch_active_repositories_via_rest(
    *,
    requester: Any,
    org_login: str,
    config: OrgConfig | None = None,
) -> dict[str, ActiveRepositoryData]:
    from github.Repository import Repository

    active_repositories: dict[str, ActiveRepositoryData] = {}
    repo_items = paginate_github_rest_list(
        requester=requester,
        path=f"/orgs/{org_login}/repos",
        parameters={"type": "all", "sort": "full_name", "direction": "asc"},
    )
    for response_headers, payload in repo_items:
        repository = Repository(
            requester=requester,
            headers=response_headers,
            attributes=payload,
            completed=True,
        )
        repository_name = cast("str | None", getattr(repository, "name", None))
        if repository_name is None or cast(
            "bool", getattr(repository, "archived", False)
        ):
            continue
        if config is not None and not config.repo_matches_filter(repository_name):
            continue
        active_repositories[repository_name] = ActiveRepositoryData(
            repository=repository,
            custom_properties=parse_repository_custom_properties(repository),
        )
    return active_repositories


def paginate_github_rest_list(
    *,
    requester: Any,
    path: str,
    parameters: dict[str, Any] | None = None,
    per_page: int = 100,
) -> list[tuple[dict[str, Any], dict[str, object]]]:
    page = 1
    items: list[tuple[dict[str, Any], dict[str, object]]] = []
    while True:
        page_parameters = dict(parameters or {})
        page_parameters["per_page"] = per_page
        page_parameters["page"] = page
        response_headers, data = requester.requestJsonAndCheck(
            "GET",
            path,
            parameters=page_parameters,
        )
        if not isinstance(data, list):
            raise RuntimeError(
                f"GitHub API call to {path} returned a non-list payload."
            )
        page_items = [item for item in data if isinstance(item, dict)]
        items.extend(
            (cast("dict[str, Any]", response_headers), item) for item in page_items
        )
        if len(data) < per_page:
            break
        page += 1
    return items


def fetch_repository_descriptions(
    organization: OrganizationLike,
) -> dict[str, str | None]:
    return {
        name: cast(
            "str | None", getattr(repository_data.repository, "description", None)
        )
        for name, repository_data in fetch_active_repositories(organization).items()
    }


def parse_repository_custom_properties(
    repository: object,
) -> dict[str, CustomPropertyValue]:
    repository_fields = vars(repository)
    preloaded_attribute = repository_fields.get("_custom_properties")
    preloaded_value = getattr(preloaded_attribute, "value", None)
    if not isinstance(preloaded_value, dict):
        return {}

    parsed: dict[str, CustomPropertyValue] = {}
    for key, value in preloaded_value.items():
        if not isinstance(key, str):
            continue
        if value is None or isinstance(value, str):
            parsed[key] = value
            continue
        if isinstance(value, list):
            parsed[key] = [item for item in value if isinstance(item, str)]
    return parsed
