from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, cast

from tqdm import tqdm

from generate_repo_overview.console import print_status
from generate_repo_overview.constants import (
    DEFAULT_CACHE,
    DEFAULT_ORG,
    DEFAULT_TOKEN_ENV,
)
from generate_repo_overview.models import (
    SNAPSHOT_SCHEMA_VERSION,
    CustomPropertyValue,
    RepoEntry,
    RepoSnapshot,
)

from .git_checkout import (
    build_authenticated_clone_url,
    clone_fresh_checkout,
    run_git_command,
    sync_repository_checkout,
    update_existing_checkout,
)
from .registry_metadata import (
    RegistrySignalsPayload,
    fetch_bazel_registry_metadata_by_repo,
    merge_bazel_registry_metadata,
    parse_bazel_registry_maintainers,
    parse_bazel_registry_metadata,
    parse_github_repository_name,
    parse_latest_bazel_registry_version,
)
from .repo_entry import (
    MERGED_PULL_REQUEST_WINDOW_DAYS,
    LatestReleaseDetails,
    PullRequestCounts,
    VolatileMetricsPayload,
    build_registry_signals,
    build_repo_entry,
    build_repo_entry_from_cached,
    cached_entry_matches_default_branch,
    cached_signals_for_repository,
    collect_volatile_metrics,
    default_latest_release_details,
    default_open_pull_request_counts,
    get_commits_since_release,
    get_default_branch_last_commit_date,
    get_default_branch_sha,
    get_latest_release_details,
    get_latest_release_version,
    get_merged_pull_request_count_last_30_days,
    get_open_issue_count,
    get_open_pull_request_counts,
    get_release_date,
    is_draft_pull_request,
    iso_date,
    normalize_datetime_utc,
    normalize_group_name,
    parse_datetime_utc,
    resolve_volatile_metrics_ttl,
    should_reuse_cached_volatile_metrics,
)
from .signal_detection import (
    DeepContentPayload,
    default_content_signals,
    detect_bazel_version,
    get_bazel_dep_version,
    get_codeowners_for_path,
    inspect_repository_content_slow,
    uses_cicd_daily_workflow,
)
from .snapshot_io import load_snapshot, load_snapshot_if_present, write_snapshot


class OrganizationLike(Protocol):
    login: str
    requester: Any


class GitHubClientLike(Protocol):
    def get_rate_limit(self) -> object: ...


@dataclass(frozen=True, slots=True)
class ActiveRepositoryData:
    repository: object
    custom_properties: dict[str, CustomPropertyValue]


DEFAULT_MAX_COLLECTION_WORKERS = 8

__all__ = [
    "ActiveRepositoryData",
    "DeepContentPayload",
    "LatestReleaseDetails",
    "PullRequestCounts",
    "RegistrySignalsPayload",
    "VolatileMetricsPayload",
    "build_authenticated_clone_url",
    "build_registry_signals",
    "build_repo_entry",
    "build_repo_entry_from_cached",
    "cached_entry_matches_default_branch",
    "cached_signals_for_repository",
    "clone_fresh_checkout",
    "collect_repository_entry",
    "collect_repository_entry_slow_path",
    "collect_snapshot",
    "collect_volatile_metrics",
    "default_content_signals",
    "default_latest_release_details",
    "default_open_pull_request_counts",
    "detect_bazel_version",
    "ensure_snapshot",
    "fetch_active_repositories",
    "fetch_active_repositories_via_rest",
    "fetch_bazel_registry_metadata_by_repo",
    "fetch_repositories",
    "fetch_repository_descriptions",
    "get_bazel_dep_version",
    "get_codeowners_for_path",
    "get_commits_since_release",
    "get_default_branch_last_commit_date",
    "get_default_branch_sha",
    "get_gh_auth_token",
    "get_latest_release_details",
    "get_latest_release_version",
    "get_merged_pull_request_count_last_30_days",
    "get_open_issue_count",
    "get_open_pull_request_counts",
    "get_release_date",
    "inspect_repository_content_slow",
    "is_draft_pull_request",
    "iso_date",
    "load_snapshot",
    "load_snapshot_if_present",
    "maybe_collect_repository_entry_fast_path",
    "merge_bazel_registry_metadata",
    "normalize_datetime_utc",
    "normalize_group_name",
    "paginate_github_rest_list",
    "parse_bazel_registry_maintainers",
    "parse_bazel_registry_metadata",
    "parse_datetime_utc",
    "parse_github_repository_name",
    "parse_latest_bazel_registry_version",
    "resolve_github_token",
    "resolve_volatile_metrics_ttl",
    "run_git_command",
    "should_reuse_cached_volatile_metrics",
    "sync_repository_checkout",
    "update_existing_checkout",
    "uses_cicd_daily_workflow",
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
    org_name: str = DEFAULT_ORG,
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
        org_name=org_name,
        token_env=token_env,
        cache_path=cache_path,
        status_prefix=status_prefix,
    )


def collect_snapshot(
    *,
    org_name: str = DEFAULT_ORG,
    token_env: str = DEFAULT_TOKEN_ENV,
    cache_path: Path | None = DEFAULT_CACHE,
    reuse_unchanged_repositories: bool = False,
    status_prefix: str = "repo-overview",
) -> RepoSnapshot:
    try:
        from github import Auth, Github
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing PyGithub. Install project dependencies before running the generator."
        ) from exc

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
    try:
        organization = github.get_organization(org_name)
        print_status("Collecting repository overview", prefix=status_prefix)
        repos = fetch_repositories(
            organization,
            existing_snapshot=existing_snapshot,
            reuse_unchanged_repositories=reuse_unchanged_repositories,
            github_token=token,
            status_prefix=status_prefix,
        )

        snapshot = RepoSnapshot(
            schema_version=SNAPSHOT_SCHEMA_VERSION,
            org_name=org_name,
            generated_at=datetime.now(UTC).isoformat(),
            repos=tuple(repos),
        )
        if cache_path is not None:
            write_snapshot(snapshot, cache_path)
            print_status(f"Wrote snapshot to {cache_path}", prefix=status_prefix)
        return snapshot
    finally:
        print_rest_api_rate_limit(
            github,
            when="after collection",
            status_prefix=status_prefix,
        )


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
    reuse_unchanged_repositories: bool = False,
    github_token: str | None = None,
    status_prefix: str = "repo-overview",
) -> list[RepoEntry]:
    print_status("Loading active repositories", prefix=status_prefix)
    active_repositories = fetch_active_repositories(organization)
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
    print_status("Loading maintainers in bazel_registry", prefix=status_prefix)
    bazel_registry_data = active_repositories.get("bazel_registry")
    bazel_registry_metadata_by_repo = fetch_bazel_registry_metadata_by_repo(
        bazel_registry_repository=(
            bazel_registry_data.repository if bazel_registry_data is not None else None
        ),
        active_repository_names=set(active_repositories),
        github_token=github_token,
    )
    print_status(
        "Loaded bazel_registry metadata for "
        f"{len(bazel_registry_metadata_by_repo)} active repositories",
        prefix=status_prefix,
    )

    cached_by_name = (
        {repo.name: repo for repo in existing_snapshot.repos}
        if existing_snapshot is not None
        else {}
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
            cached_entry = cached_by_name.get(repository_name)
            future = executor.submit(
                collect_repository_entry,
                repository_name=repository_name,
                repository=repository_data.repository,
                custom_properties=repository_data.custom_properties,
                bazel_registry_metadata=bazel_registry_metadata_by_repo.get(
                    repository_name
                ),
                cached_entry=cached_entry,
                reuse_cached_entry_when_unchanged=reuse_unchanged_repositories,
            )
            futures[future] = (index, repository_name)

        for future in as_completed(futures):
            index, repository_name = futures[future]
            repos_by_index[index] = future.result()
            progress.update(1)
            progress.set_postfix_str(repository_name)

    return [repos_by_index[index] for index in range(1, total_repositories + 1)]


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
) -> dict[str, ActiveRepositoryData]:
    return fetch_active_repositories_via_rest(
        requester=organization.requester,
        org_login=organization.login,
    )


def fetch_active_repositories_via_rest(
    *,
    requester: Any,
    org_login: str,
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
        if repository_name is None or cast("bool", getattr(repository, "archived", False)):
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
            raise RuntimeError(f"GitHub API call to {path} returned a non-list payload.")
        page_items = [item for item in data if isinstance(item, dict)]
        items.extend((cast("dict[str, Any]", response_headers), item) for item in page_items)
        if len(data) < per_page:
            break
        page += 1
    return items


def fetch_repository_descriptions(
    organization: OrganizationLike,
) -> dict[str, str | None]:
    return {
        name: cast("str | None", getattr(repository_data.repository, "description", None))
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


def collect_repository_entry(
    *,
    repository_name: str,
    repository: Any,
    custom_properties: dict[str, CustomPropertyValue],
    bazel_registry_metadata: RegistrySignalsPayload | None,
    cached_entry: RepoEntry | None,
    reuse_cached_entry_when_unchanged: bool = False,
) -> RepoEntry:
    """Collect one repository entry using explicit fast/slow collection paths.

    Fast path: when cache reuse is enabled and default-branch state is unchanged,
    reuse cached content indicators and optionally cached volatile metrics.

    Slow path: when cache reuse is impossible (or disabled), inspect repository
    content and refresh volatile metrics from live API calls.
    """
    fast_entry = maybe_collect_repository_entry_fast_path(
        repository_name=repository_name,
        repository=repository,
        custom_properties=custom_properties,
        bazel_registry_metadata=bazel_registry_metadata,
        cached_entry=cached_entry,
        reuse_cached_entry_when_unchanged=reuse_cached_entry_when_unchanged,
    )
    if fast_entry is not None:
        return fast_entry

    return collect_repository_entry_slow_path(
        repository_name=repository_name,
        repository=repository,
        custom_properties=custom_properties,
        bazel_registry_metadata=bazel_registry_metadata,
        cached_entry=cached_entry,
    )


def maybe_collect_repository_entry_fast_path(
    *,
    repository_name: str,
    repository: Any,
    custom_properties: dict[str, CustomPropertyValue],
    bazel_registry_metadata: RegistrySignalsPayload | None,
    cached_entry: RepoEntry | None,
    reuse_cached_entry_when_unchanged: bool,
) -> RepoEntry | None:
    """Attempt a fast collection path that avoids deep content inspection.

    Returns ``None`` when the fast path is not applicable.
    """
    default_branch = cast("str | None", getattr(repository, "default_branch", None))
    default_branch_sha = get_default_branch_sha(repository, default_branch)
    cache_matches_default_branch = cached_entry_matches_default_branch(
        cached_entry,
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
    )

    if not (reuse_cached_entry_when_unchanged and cache_matches_default_branch):
        return None

    assert cached_entry is not None
    if should_reuse_cached_volatile_metrics(cached_entry):
        return build_repo_entry_from_cached(
            cached_entry=cached_entry,
            repository_name=repository_name,
            description=cast("str | None", getattr(repository, "description", None)),
            custom_properties=custom_properties,
            default_branch=default_branch,
            default_branch_sha=default_branch_sha,
            bazel_registry_metadata=bazel_registry_metadata,
            stars=getattr(repository, "stargazers_count", 0) or 0,
            forks=getattr(repository, "forks_count", 0) or 0,
        )

    # Medium-fast variant: keep cached content indicators but refresh volatile API metrics.
    content_signals = cached_signals_for_repository(
        cached_entry,
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
    )
    assert content_signals is not None
    volatile_metrics = collect_volatile_metrics(
        repository,
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
    )
    registry_signals = build_registry_signals(bazel_registry_metadata)
    return build_repo_entry(
        repository_name=repository_name,
        description=cast("str | None", getattr(repository, "description", None)),
        custom_properties=custom_properties,
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
        content_signals=content_signals,
        registry_signals=registry_signals,
        volatile_metrics=volatile_metrics,
        volatile_metrics_fetched_at=datetime.now(UTC).isoformat(),
        stars=getattr(repository, "stargazers_count", 0) or 0,
        forks=getattr(repository, "forks_count", 0) or 0,
    )


def collect_repository_entry_slow_path(
    *,
    repository_name: str,
    repository: Any,
    custom_properties: dict[str, CustomPropertyValue],
    bazel_registry_metadata: RegistrySignalsPayload | None,
    cached_entry: RepoEntry | None,
) -> RepoEntry:
    """Collect using slow path logic (deep content inspection when cache can't prove reuse)."""
    default_branch = cast("str | None", getattr(repository, "default_branch", None))
    default_branch_sha = get_default_branch_sha(repository, default_branch)

    cached_content_signals = cached_signals_for_repository(
        cached_entry,
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
    )

    if cached_content_signals is None:
        content_signals = inspect_repository_content_slow(
            repository,
            ref=default_branch_sha,
        )
    else:
        content_signals = cached_content_signals
    volatile_metrics = collect_volatile_metrics(
        repository,
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
    )
    registry_signals = build_registry_signals(bazel_registry_metadata)

    return build_repo_entry(
        repository_name=repository_name,
        description=cast("str | None", getattr(repository, "description", None)),
        custom_properties=custom_properties,
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
        content_signals=content_signals,
        registry_signals=registry_signals,
        volatile_metrics=volatile_metrics,
        volatile_metrics_fetched_at=datetime.now(UTC).isoformat(),
        stars=getattr(repository, "stargazers_count", 0) or 0,
        forks=getattr(repository, "forks_count", 0) or 0,
    )
