from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, cast
from urllib.parse import quote, urlsplit, urlunsplit

from tqdm import tqdm

from .console import print_status
from .constants import DEFAULT_CACHE, DEFAULT_ORG, DEFAULT_TOKEN_ENV
from .models import (
    DEFAULT_CATEGORY,
    DEFAULT_SUBCATEGORY,
    SNAPSHOT_SCHEMA_VERSION,
    CustomPropertyValue,
    DeepContentSignals,
    RegistrySignals,
    RepoEntry,
    RepoSnapshot,
    VolatileMetricsSnapshot,
)

if TYPE_CHECKING:
    import collections.abc


class PullRequestCounts(TypedDict):
    ready: int
    draft: int
    total: int


class LatestReleaseDetails(TypedDict):
    version: str | None
    date: str | None
    commits_since_release: int | None


class VolatileMetricsPayload(TypedDict):
    last_push_date: str | None
    merged_prs_30_days: int
    open_issues: int
    open_prs: int
    open_ready_prs: int
    open_draft_prs: int
    latest_release_version: str | None
    latest_release_date: str | None
    commits_since_latest_release: int | None


class DeepContentPayload(TypedDict):
    is_bazel_repo: bool
    bazel_version: str | None
    codeowners: tuple[str, ...]
    docs_as_code_version: str | None
    has_gitlint_config: bool
    has_pyproject_toml: bool
    has_pre_commit_config: bool
    has_lint_config: bool
    has_ci: bool
    uses_cicd_daily_workflow: bool
    has_coverage_config: bool


class RegistrySignalsPayload(TypedDict):
    maintainers_in_bazel_registry: tuple[str, ...]
    latest_bazel_registry_version: str | None


@dataclass(frozen=True, slots=True)
class ActiveRepositoryData:
    repository: object
    custom_properties: dict[str, CustomPropertyValue]


class OrganizationLike(Protocol):
    login: str
    requester: Any


class GitHubClientLike(Protocol):
    def get_rate_limit(self) -> object: ...


GITLINT_PATHS = (".gitlint",)
PYPROJECT_PATHS = ("pyproject.toml",)
PRE_COMMIT_PATHS = (".pre-commit-config.yaml",)
LINT_CONFIG_PATHS = GITLINT_PATHS + PRE_COMMIT_PATHS
CI_PATHS = (".github/workflows",)
COVERAGE_PATHS = ("coverage.yml", "coverage.xml", "pytest.ini", ".coveragerc")
BAZEL_VERSION_PATHS = (".bazelversion",)
MODULE_PATHS = ("MODULE.bazel",)
BAZEL_REPO_MARKER_PATHS = (
    BAZEL_VERSION_PATHS
    + MODULE_PATHS
    + (
        "WORKSPACE",
        "WORKSPACE.bazel",
    )
)
CODEOWNERS_PATH = ".github/CODEOWNERS"
WORKFLOW_PATH_PREFIX = ".github/workflows/"
WORKFLOW_FILE_SUFFIXES = (".yml", ".yaml")
DAILY_WORKFLOW_REFERENCE = "cicd-workflows/.github/workflows/daily.yml@"
BAZEL_REGISTRY_LOCAL_CHECKOUT = Path("profile/cache/bazel_registry_checkout")
BAZEL_DEP_PATTERN_TEMPLATE = (
    r'\bbazel_dep\s*\(\s*name\s*=\s*"{module_name}"(?P<body>.*?)\)'
)
VERSION_PATTERN = re.compile(r'\bversion\s*=\s*"(?P<version>[^"]+)"')
DEFAULT_MAX_COLLECTION_WORKERS = 8
MERGED_PULL_REQUEST_WINDOW_DAYS = 30
DEFAULT_VOLATILE_METRICS_TTL_MINUTES = 60
VOLATILE_METRICS_TTL_ENV = "REPO_OVERVIEW_VOLATILE_TTL_MINUTES"


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


def load_snapshot(path: Path) -> RepoSnapshot:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Snapshot file must contain a JSON object.")
    return RepoSnapshot.from_dict(raw)


def load_snapshot_if_present(path: Path) -> RepoSnapshot | None:
    if not path.exists():
        return None
    try:
        return load_snapshot(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def write_snapshot(snapshot: RepoSnapshot, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = snapshot.to_dict()
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
    custom_properties_by_name = {
        repository_name: repository_data.custom_properties
        for repository_name, repository_data in active_repositories.items()
        if repository_data.custom_properties
    }
    print_status(
        f"Extracted custom properties for {len(custom_properties_by_name)} repositories",
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


def fetch_bazel_registry_metadata_by_repo(
    *,
    bazel_registry_repository: object | None,
    active_repository_names: set[str],
    github_token: str | None,
) -> dict[str, RegistrySignalsPayload]:
    if bazel_registry_repository is None:
        return {}

    default_branch = cast("str | None", getattr(bazel_registry_repository, "default_branch", None))
    clone_url = cast("str | None", getattr(bazel_registry_repository, "clone_url", None))
    if default_branch is None or clone_url is None:
        return {}

    checkout_path = sync_repository_checkout(
        clone_url=clone_url,
        default_branch=default_branch,
        github_token=github_token,
        checkout_path=BAZEL_REGISTRY_LOCAL_CHECKOUT,
    )
    if checkout_path is None:
        return {}

    metadata_paths = sorted(checkout_path.glob("modules/*/metadata.json"))

    metadata_by_repo_name: dict[str, RegistrySignalsPayload] = {}
    for metadata_path in metadata_paths:
        try:
            content = metadata_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for repository_name, metadata in parse_bazel_registry_metadata(
            content,
            active_repository_names=active_repository_names,
        ).items():
            metadata_by_repo_name[repository_name] = merge_bazel_registry_metadata(
                metadata_by_repo_name.get(repository_name),
                metadata,
            )
    return metadata_by_repo_name


def sync_repository_checkout(
    *,
    clone_url: str,
    default_branch: str,
    github_token: str | None,
    checkout_path: Path,
) -> Path | None:
    authenticated_url = build_authenticated_clone_url(clone_url, github_token)
    checkout_path.parent.mkdir(parents=True, exist_ok=True)

    if update_existing_checkout(checkout_path, default_branch):
        return checkout_path

    if (checkout_path / ".git").exists():
        shutil.rmtree(checkout_path, ignore_errors=True)

    if not clone_fresh_checkout(
        authenticated_url=authenticated_url,
        default_branch=default_branch,
        checkout_path=checkout_path,
    ):
        return None

    return checkout_path


def update_existing_checkout(checkout_path: Path, default_branch: str) -> bool:
    git_dir = checkout_path / ".git"
    if not git_dir.exists():
        return False

    fetch_ok = run_git_command(
        [
            "git",
            "-C",
            str(checkout_path),
            "fetch",
            "--depth",
            "1",
            "origin",
            default_branch,
        ]
    )
    checkout_ok = run_git_command(
        [
            "git",
            "-C",
            str(checkout_path),
            "checkout",
            "--force",
            "--detach",
            "FETCH_HEAD",
        ]
    )
    if not (fetch_ok and checkout_ok):
        return False

    run_git_command(["git", "-C", str(checkout_path), "clean", "-fdx"])
    return True


def clone_fresh_checkout(
    *,
    authenticated_url: str,
    default_branch: str,
    checkout_path: Path,
) -> bool:
    shutil.rmtree(checkout_path, ignore_errors=True)
    return run_git_command(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            default_branch,
            authenticated_url,
            str(checkout_path),
        ]
    )


def run_git_command(command: list[str]) -> bool:
    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def build_authenticated_clone_url(clone_url: str, github_token: str | None) -> str:
    if github_token is None:
        return clone_url

    parsed = urlsplit(clone_url)
    auth = f"x-access-token:{quote(github_token, safe='')}"
    netloc = f"{auth}@{parsed.netloc}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def parse_bazel_registry_metadata(
    text: str | None,
    *,
    active_repository_names: set[str],
) -> dict[str, RegistrySignalsPayload]:
    if not text:
        return {}
    try:
        raw_metadata_object: object = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw_metadata_object, dict):
        return {}
    raw_metadata = cast("dict[str, object]", raw_metadata_object)

    maintainers = parse_bazel_registry_maintainers(raw_metadata.get("maintainers"))
    latest_version = parse_latest_bazel_registry_version(raw_metadata.get("versions"))

    metadata_by_repo_name: dict[str, RegistrySignalsPayload] = {}
    raw_repositories = raw_metadata.get("repository")
    if not isinstance(raw_repositories, list):
        return metadata_by_repo_name

    repository_entries = cast("list[object]", raw_repositories)
    for raw_repository in repository_entries:
        repository_name = parse_github_repository_name(raw_repository)
        if repository_name is None or repository_name not in active_repository_names:
            continue
        metadata_by_repo_name[repository_name] = {
            "maintainers_in_bazel_registry": maintainers,
            "latest_bazel_registry_version": latest_version,
        }

    return metadata_by_repo_name


def parse_bazel_registry_maintainers(raw_maintainers: object) -> tuple[str, ...]:
    if not isinstance(raw_maintainers, list):
        return ()

    maintainers: list[str] = []
    maintainer_entries = cast("list[object]", raw_maintainers)
    for raw_maintainer in maintainer_entries:
        if not isinstance(raw_maintainer, dict):
            continue
        maintainer = cast("dict[str, object]", raw_maintainer)

        name = maintainer.get("name")
        github_handle = maintainer.get("github")
        email = maintainer.get("email")

        display_parts: list[str] = []
        if isinstance(name, str) and name.strip():
            display_parts.append(name.strip())
        if isinstance(github_handle, str) and github_handle.strip():
            display_parts.append(f"(@{github_handle.strip()})")
        if not display_parts and isinstance(email, str) and email.strip():
            display_parts.append(email.strip())
        if display_parts:
            maintainers.append(" ".join(display_parts))

    return dedupe_preserving_order(maintainers)


def parse_latest_bazel_registry_version(raw_versions: object) -> str | None:
    if not isinstance(raw_versions, list):
        return None
    version_entries = cast("list[object]", raw_versions)
    for raw_version in version_entries:
        if isinstance(raw_version, str) and raw_version.strip():
            return raw_version.strip()
    return None


def parse_github_repository_name(value: object) -> str | None:
    if not isinstance(value, str) or not value.startswith("github:"):
        return None

    owner_and_repo = value.removeprefix("github:")
    if "/" not in owner_and_repo:
        return None

    _, repository_name = owner_and_repo.split("/", maxsplit=1)
    repository_name = repository_name.strip()
    return repository_name or None


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


def collect_volatile_metrics(
    repository: Any,
    *,
    default_branch: str | None,
    default_branch_sha: str | None,
) -> VolatileMetricsPayload:
    """Collect volatile metrics from live API calls.

    This is comparatively slow and intentionally refreshed on demand based on
    the configured volatile-metric TTL.
    """
    open_pull_request_counts = get_open_pull_request_counts(repository)
    merged_pull_request_count = get_merged_pull_request_count_last_30_days(
        repository,
        default_branch=default_branch,
    )
    latest_release = get_latest_release_details(
        repository,
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
    )
    last_commit_date = get_default_branch_last_commit_date(
        repository,
        default_branch=default_branch,
    )
    return {
        "last_push_date": last_commit_date
        or iso_date(getattr(repository, "pushed_at", None)),
        "merged_prs_30_days": merged_pull_request_count,
        "open_issues": get_open_issue_count(
            repository,
            open_pull_request_total=open_pull_request_counts["total"],
        ),
        "open_prs": open_pull_request_counts["total"],
        "open_ready_prs": open_pull_request_counts["ready"],
        "open_draft_prs": open_pull_request_counts["draft"],
        "latest_release_version": latest_release["version"],
        "latest_release_date": latest_release["date"],
        "commits_since_latest_release": latest_release["commits_since_release"],
    }


def get_default_branch_last_commit_date(
    repository: Any,
    *,
    default_branch: str | None,
) -> str | None:
    if not default_branch:
        return None

    try:
        branch = repository.get_branch(default_branch)
    except Exception:
        return None

    commit = getattr(branch, "commit", None)
    nested_commit = getattr(commit, "commit", None)
    committer = getattr(nested_commit, "committer", None)
    timestamp = getattr(committer, "date", None)
    return iso_date(timestamp)


def cached_signals_for_repository(
    cached_entry: RepoEntry | None,
    *,
    default_branch: str | None,
    default_branch_sha: str | None,
) -> DeepContentPayload | None:
    if not cached_entry_matches_default_branch(
        cached_entry,
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
    ):
        return None

    return {
        "is_bazel_repo": cached_entry.content.is_bazel_repo,
        "bazel_version": cached_entry.content.bazel_version,
        "codeowners": cached_entry.content.codeowners,
        "docs_as_code_version": cached_entry.content.docs_as_code_version,
        "has_lint_config": cached_entry.content.has_lint_config,
        "has_gitlint_config": cached_entry.content.has_gitlint_config,
        "has_pyproject_toml": cached_entry.content.has_pyproject_toml,
        "has_pre_commit_config": cached_entry.content.has_pre_commit_config,
        "has_ci": cached_entry.content.has_ci,
        "uses_cicd_daily_workflow": cached_entry.content.uses_cicd_daily_workflow,
        "has_coverage_config": cached_entry.content.has_coverage_config,
    }


def cached_entry_matches_default_branch(
    cached_entry: RepoEntry | None,
    *,
    default_branch: str | None,
    default_branch_sha: str | None,
) -> bool:
    if cached_entry is None:
        return False

    # Reuse cached repository details only when we can prove the default-branch state is unchanged.
    cached_sha = cached_entry.default_branch_sha
    if default_branch_sha is not None:
        return cached_sha == default_branch_sha

    if default_branch is not None:
        return cached_entry.default_branch == default_branch

    return False


def build_repo_entry_from_cached(
    *,
    cached_entry: RepoEntry,
    repository_name: str,
    description: str | None,
    custom_properties: dict[str, CustomPropertyValue],
    default_branch: str | None,
    default_branch_sha: str | None,
    bazel_registry_metadata: RegistrySignalsPayload | None,
    stars: int,
    forks: int,
) -> RepoEntry:
    registry = build_registry_signals(bazel_registry_metadata)
    return replace(
        cached_entry,
        name=repository_name,
        description=description or "(no description)",
        category=normalize_group_name(
            custom_properties.get("category"), DEFAULT_CATEGORY
        ),
        subcategory=normalize_group_name(
            custom_properties.get("subcategory"),
            DEFAULT_SUBCATEGORY,
        ),
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
        registry=registry,
        stars=stars,
        forks=forks,
    )


def build_repo_entry(
    repository_name: str,
    description: str | None,
    custom_properties: dict[str, CustomPropertyValue],
    *,
    default_branch: str | None = None,
    default_branch_sha: str | None = None,
    content_signals: DeepContentPayload,
    registry_signals: RegistrySignals,
    volatile_metrics: VolatileMetricsPayload,
    volatile_metrics_fetched_at: str | None = None,
    stars: int = 0,
    forks: int = 0,
) -> RepoEntry:
    category = normalize_group_name(custom_properties.get("category"), DEFAULT_CATEGORY)
    subcategory = normalize_group_name(
        custom_properties.get("subcategory"),
        DEFAULT_SUBCATEGORY,
    )
    return RepoEntry(
        name=repository_name,
        description=description or "(no description)",
        category=category,
        subcategory=subcategory,
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
        content=DeepContentSignals(
            is_bazel_repo=content_signals["is_bazel_repo"],
            bazel_version=content_signals["bazel_version"],
            codeowners=content_signals["codeowners"],
            docs_as_code_version=content_signals["docs_as_code_version"],
            has_lint_config=content_signals["has_lint_config"],
            has_gitlint_config=bool(content_signals.get("has_gitlint_config", False)),
            has_pyproject_toml=bool(content_signals.get("has_pyproject_toml", False)),
            has_pre_commit_config=bool(
                content_signals.get("has_pre_commit_config", False)
            ),
            has_ci=content_signals["has_ci"],
            uses_cicd_daily_workflow=content_signals["uses_cicd_daily_workflow"],
            has_coverage_config=content_signals["has_coverage_config"],
        ),
        registry=registry_signals,
        volatile=VolatileMetricsSnapshot(
            last_push_date=volatile_metrics["last_push_date"],
            merged_prs_30_days=volatile_metrics["merged_prs_30_days"],
            open_issues=volatile_metrics["open_issues"],
            open_prs=volatile_metrics["open_prs"],
            open_ready_prs=volatile_metrics["open_ready_prs"],
            open_draft_prs=volatile_metrics["open_draft_prs"],
            latest_release_version=volatile_metrics["latest_release_version"],
            latest_release_date=volatile_metrics["latest_release_date"],
            commits_since_latest_release=volatile_metrics[
                "commits_since_latest_release"
            ],
            volatile_metrics_fetched_at=volatile_metrics_fetched_at,
        ),
        stars=stars,
        forks=forks,
    )


def should_reuse_cached_volatile_metrics(cached_entry: RepoEntry) -> bool:
    fetched_at = parse_datetime_utc(cached_entry.volatile.volatile_metrics_fetched_at)
    if fetched_at is None:
        return False
    ttl = resolve_volatile_metrics_ttl()
    return datetime.now(UTC) - fetched_at <= ttl


def build_registry_signals(
    metadata: RegistrySignalsPayload | None,
) -> RegistrySignals:
    return RegistrySignals(
        maintainers_in_bazel_registry=(
            metadata.get("maintainers_in_bazel_registry")
            if metadata is not None
            else ()
        ),
        latest_bazel_registry_version=(
            metadata.get("latest_bazel_registry_version")
            if metadata is not None
            else None
        ),
    )


def resolve_volatile_metrics_ttl() -> timedelta:
    raw_value = os.getenv(VOLATILE_METRICS_TTL_ENV, "").strip()
    if not raw_value:
        return timedelta(minutes=DEFAULT_VOLATILE_METRICS_TTL_MINUTES)

    try:
        parsed_minutes = int(raw_value)
    except ValueError:
        return timedelta(minutes=DEFAULT_VOLATILE_METRICS_TTL_MINUTES)

    if parsed_minutes < 0:
        return timedelta(minutes=DEFAULT_VOLATILE_METRICS_TTL_MINUTES)
    return timedelta(minutes=parsed_minutes)


def parse_datetime_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_group_name(value: str | list[str] | None, fallback: str) -> str:
    if value is None:
        return fallback
    if isinstance(value, list):
        cleaned = [item.strip() for item in value if item.strip()]
        return ", ".join(cleaned) if cleaned else fallback
    cleaned = value.strip()
    return cleaned or fallback


def inspect_repository_content_slow(
    repository: Any,
    *,
    ref: str | None,
) -> DeepContentPayload:
    """Run slow deep content inspection using repository tree and file reads."""
    tree_paths = fetch_repository_tree_paths(repository, ref=ref)
    if not tree_paths:
        return default_content_signals()

    return {
        "is_bazel_repo": detect_is_bazel_repo(tree_paths),
        "bazel_version": detect_bazel_version(
            repository,
            tree_paths=tree_paths,
            ref=ref,
        ),
        "codeowners": detect_codeowners(
            repository,
            tree_paths=tree_paths,
            ref=ref,
        ),
        "docs_as_code_version": detect_dependency_version(
            repository,
            tree_paths=tree_paths,
            ref=ref,
            module_name="score_docs_as_code",
        ),
        "has_gitlint_config": any(
            tree_contains_path(tree_paths, path) for path in GITLINT_PATHS
        ),
        "has_pyproject_toml": any(
            tree_contains_path(tree_paths, path) for path in PYPROJECT_PATHS
        ),
        "has_pre_commit_config": any(
            tree_contains_path(tree_paths, path) for path in PRE_COMMIT_PATHS
        ),
        "has_lint_config": any(
            tree_contains_path(tree_paths, path) for path in LINT_CONFIG_PATHS
        ),
        "has_ci": any(tree_contains_path(tree_paths, path) for path in CI_PATHS),
        "uses_cicd_daily_workflow": uses_cicd_daily_workflow(
            repository,
            tree_paths=tree_paths,
            ref=ref,
        ),
        "has_coverage_config": any(
            tree_contains_path(tree_paths, path) for path in COVERAGE_PATHS
        ),
    }


def default_content_signals() -> DeepContentPayload:
    return {
        "is_bazel_repo": False,
        "bazel_version": None,
        "codeowners": (),
        "docs_as_code_version": None,
        "has_gitlint_config": False,
        "has_pyproject_toml": False,
        "has_pre_commit_config": False,
        "has_lint_config": False,
        "has_ci": False,
        "uses_cicd_daily_workflow": False,
        "has_coverage_config": False,
    }


def fetch_repository_tree_paths(repository: Any, *, ref: str | None) -> set[str]:
    if ref is None or not hasattr(repository, "get_git_tree"):
        return set()

    try:
        tree = repository.get_git_tree(ref, recursive=True)
    except Exception:
        return set()

    return {
        path
        for item in getattr(tree, "tree", [])
        if isinstance((path := getattr(item, "path", None)), str)
    }


def tree_contains_path(tree_paths: set[str], candidate: str) -> bool:
    if candidate in tree_paths:
        return True
    prefix = f"{candidate}/"
    return any(path.startswith(prefix) for path in tree_paths)


def detect_bazel_version(
    repository: Any,
    *,
    tree_paths: set[str],
    ref: str | None,
) -> str | None:
    for candidate in BAZEL_VERSION_PATHS:
        if not tree_contains_path(tree_paths, candidate):
            continue
        content = fetch_text_file(repository, candidate, ref=ref)
        version = first_non_comment_line(content)
        if version:
            return version

    return None


def detect_is_bazel_repo(tree_paths: set[str]) -> bool:
    return any(
        tree_contains_path(tree_paths, candidate)
        for candidate in BAZEL_REPO_MARKER_PATHS
    )


def detect_dependency_version(
    repository: Any,
    *,
    tree_paths: set[str],
    ref: str | None,
    module_name: str,
) -> str | None:
    for candidate in MODULE_PATHS:
        if not tree_contains_path(tree_paths, candidate):
            continue
        content = fetch_text_file(repository, candidate, ref=ref)
        version = get_bazel_dep_version(content, module_name=module_name)
        if version:
            return version

    return None


def detect_codeowners(
    repository: Any,
    *,
    tree_paths: set[str],
    ref: str | None,
) -> tuple[str, ...]:
    if not tree_contains_path(tree_paths, CODEOWNERS_PATH):
        return ()

    content = fetch_text_file(repository, CODEOWNERS_PATH, ref=ref)
    return get_codeowners_for_path(content, target_path=CODEOWNERS_PATH)


def get_codeowners_for_path(
    text: str | None,
    *,
    target_path: str,
) -> tuple[str, ...]:
    if not text:
        return ()

    owners: tuple[str, ...] = ()
    for raw_line in text.splitlines():
        line = raw_line.split("#", maxsplit=1)[0].strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        pattern, *candidate_owners = parts
        if codeowners_pattern_matches(pattern, target_path=target_path):
            owners = normalize_codeowners(candidate_owners)

    return owners


def codeowners_pattern_matches(pattern: str, *, target_path: str) -> bool:
    normalized_pattern = pattern.lstrip("/")
    normalized_target_path = target_path.lstrip("/")

    if pattern == "/":
        return True
    if normalized_pattern in {"*", "**", "/*"}:
        return True

    if normalized_pattern.endswith("/"):
        directory_pattern = normalized_pattern.rstrip("/")
        return (
            normalized_target_path == directory_pattern
            or normalized_target_path.startswith(f"{directory_pattern}/")
        )

    if "/" not in normalized_pattern:
        # Bare patterns can match either the basename or the full path, mirroring CODEOWNERS behavior.
        return fnmatch.fnmatch(
            normalized_target_path.rsplit("/", maxsplit=1)[-1],
            normalized_pattern,
        ) or fnmatch.fnmatch(normalized_target_path, normalized_pattern)

    return fnmatch.fnmatch(normalized_target_path, normalized_pattern)


def get_bazel_dep_version(text: str | None, *, module_name: str) -> str | None:
    if not text:
        return None

    pattern = re.compile(
        BAZEL_DEP_PATTERN_TEMPLATE.format(module_name=re.escape(module_name)),
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        return None

    version_match = VERSION_PATTERN.search(match.group("body"))
    if version_match is None:
        return None

    version = version_match.group("version").strip()
    return version or None


def uses_cicd_daily_workflow(
    repository: Any,
    *,
    tree_paths: set[str],
    ref: str | None,
) -> bool:
    workflow_paths = sorted(
        path
        for path in tree_paths
        if path.startswith(WORKFLOW_PATH_PREFIX)
        and path.endswith(WORKFLOW_FILE_SUFFIXES)
    )
    for workflow_path in workflow_paths:
        content = fetch_text_file(repository, workflow_path, ref=ref)
        if content is None:
            continue
        if DAILY_WORKFLOW_REFERENCE in content:
            return True
    return False


def fetch_text_file(repository: Any, path: str, *, ref: str | None) -> str | None:
    if not hasattr(repository, "get_contents"):
        return None

    try:
        if ref is None:
            content = repository.get_contents(path)
        else:
            content = repository.get_contents(path, ref=ref)
    except Exception:
        return None

    raw_content = getattr(content, "decoded_content", None)
    if not isinstance(raw_content, (bytes, bytearray)):
        return None
    return raw_content.decode("utf-8", errors="replace")


def merge_bazel_registry_metadata(
    existing: RegistrySignalsPayload | None,
    incoming: RegistrySignalsPayload,
) -> RegistrySignalsPayload:
    if existing is None:
        return incoming

    return {
        "maintainers_in_bazel_registry": dedupe_preserving_order(
            list(existing["maintainers_in_bazel_registry"])
            + list(incoming["maintainers_in_bazel_registry"])
        ),
        "latest_bazel_registry_version": existing["latest_bazel_registry_version"]
        or incoming["latest_bazel_registry_version"],
    }


def normalize_codeowners(values: list[str]) -> tuple[str, ...]:
    return dedupe_preserving_order(" ".join(values).replace(",", " ").split())


def dedupe_preserving_order(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
    return tuple(deduped)


def first_non_comment_line(text: str | None) -> str | None:
    if not text:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped
    return None


def get_default_branch_sha(repository: Any, default_branch: str | None) -> str | None:
    if default_branch is None or not hasattr(repository, "get_branch"):
        return None

    try:
        branch = repository.get_branch(default_branch)
    except Exception:
        return None
    return cast("str | None", getattr(getattr(branch, "commit", None), "sha", None))


def get_open_issue_count(repository: Any, *, open_pull_request_total: int) -> int:
    count = getattr(repository, "open_issues_count", 0)
    if not isinstance(count, int):
        return 0
    return max(count - open_pull_request_total, 0)


def get_open_pull_request_counts(repository: Any) -> PullRequestCounts:
    try:
        pulls = repository.get_pulls(state="open")
    except Exception:
        return default_open_pull_request_counts()

    try:
        pull_requests = list(pulls)
    except Exception:
        return default_open_pull_request_counts()

    draft_count = sum(
        is_draft_pull_request(pull_request) for pull_request in pull_requests
    )
    total_count = len(pull_requests)
    return {
        "ready": total_count - draft_count,
        "draft": draft_count,
        "total": total_count,
    }


def get_merged_pull_request_count_last_30_days(
    repository: Any,
    *,
    default_branch: str | None,
) -> int:
    if default_branch is None:
        return 0

    cutoff = datetime.now(UTC) - timedelta(days=MERGED_PULL_REQUEST_WINDOW_DAYS)
    try:
        pulls = repository.get_pulls(
            state="closed",
            sort="updated",
            direction="desc",
            base=default_branch,
        )
    except Exception:
        return 0

    count = 0
    for pull_request in pulls:
        updated_at = normalize_datetime_utc(getattr(pull_request, "updated_at", None))
        # With descending `updated` ordering, once we pass the cutoff we can stop scanning.
        if updated_at is not None and updated_at < cutoff:
            break

        base = getattr(pull_request, "base", None)
        base_ref = getattr(base, "ref", None)
        if isinstance(base_ref, str) and base_ref != default_branch:
            continue

        merged_at = normalize_datetime_utc(getattr(pull_request, "merged_at", None))
        if merged_at is None or merged_at < cutoff:
            continue
        count += 1

    return count


def normalize_datetime_utc(value: object) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    # Treat naive timestamps as UTC so comparisons stay deterministic.
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def default_open_pull_request_counts() -> PullRequestCounts:
    return {"ready": 0, "draft": 0, "total": 0}


def is_draft_pull_request(pull_request: Any) -> bool:
    draft: object
    try:
        draft = getattr(pull_request, "draft", None)
    except Exception:
        draft = None
    if isinstance(draft, bool):
        return draft

    try:
        raw_data = getattr(pull_request, "raw_data", None)
    except Exception:
        raw_data = None
    if isinstance(raw_data, dict):
        draft = cast("object", raw_data.get("draft"))
        if isinstance(draft, bool):
            return draft
    return False


def get_latest_release_details(
    repository: Any,
    *,
    default_branch: str | None,
    default_branch_sha: str | None,
) -> LatestReleaseDetails:
    if not hasattr(repository, "get_latest_release"):
        return default_latest_release_details()
    try:
        release = repository.get_latest_release()
    except Exception:
        return default_latest_release_details()

    return {
        "version": get_latest_release_version(release),
        "date": get_release_date(release),
        "commits_since_release": get_commits_since_release(
            repository,
            release=release,
            default_branch=default_branch,
            default_branch_sha=default_branch_sha,
        ),
    }


def default_latest_release_details() -> LatestReleaseDetails:
    return {
        "version": None,
        "date": None,
        "commits_since_release": None,
    }


def get_latest_release_version(release: object) -> str | None:
    try:
        raw_data = getattr(release, "raw_data", None)
    except Exception:
        raw_data = None
    if isinstance(raw_data, dict):
        raw_data = cast("dict[str, object]", raw_data)
        for key in ("tag_name", "name"):
            value = raw_data.get(key)
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    return cleaned

    for attribute_name in ("name", "title"):
        try:
            value = getattr(release, attribute_name, None)
        except Exception:
            continue
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned and cleaned.casefold() != "latest":
                return cleaned
    return None


def get_release_date(release: object) -> str | None:
    try:
        return iso_date(getattr(release, "published_at", None))
    except Exception:
        return None


def get_commits_since_release(
    repository: Any,
    *,
    release: Any,
    default_branch: str | None,
    default_branch_sha: str | None,
) -> int | None:
    if not hasattr(repository, "compare"):
        return None

    release_tag = get_latest_release_version(release)
    head_ref = default_branch_sha or default_branch
    if release_tag is None or head_ref is None:
        return None

    try:
        comparison = repository.compare(release_tag, head_ref)
    except Exception:
        return None

    try:
        total_commits = getattr(comparison, "total_commits", None)
        if isinstance(total_commits, int):
            return total_commits

        total_commits = getattr(comparison, "totalCommits", None)
        return total_commits if isinstance(total_commits, int) else None
    except Exception:
        return None


def iso_date(value: object) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return None
