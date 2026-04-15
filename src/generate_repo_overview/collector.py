from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from .console import print_status
from .constants import DEFAULT_CACHE, DEFAULT_ORG, DEFAULT_TOKEN_ENV
from .models import (
    DEFAULT_CATEGORY,
    DEFAULT_SUBCATEGORY,
    SNAPSHOT_SCHEMA_VERSION,
    CustomPropertyValue,
    RepoEntry,
    RepoSnapshot,
    snapshot_from_dict,
    snapshot_to_dict,
)

if TYPE_CHECKING:
    from pathlib import Path

    from github.Organization import Organization

LINT_CONFIG_PATHS = (".gitlint", ".editorconfig", ".pre-commit-config.yaml")
CI_PATHS = (".github/workflows",)
COVERAGE_PATHS = ("coverage.yml", "coverage.xml", "pytest.ini", ".coveragerc")
BAZEL_VERSION_PATHS = (".bazelversion",)
MODULE_PATHS = ("MODULE.bazel",)
WORKFLOW_PATH_PREFIX = ".github/workflows/"
WORKFLOW_FILE_SUFFIXES = (".yml", ".yaml")
DAILY_WORKFLOW_REFERENCE = "cicd-workflows/.github/workflows/daily.yml@"
BAZEL_DEP_PATTERN_TEMPLATE = (
    r'\bbazel_dep\s*\(\s*name\s*=\s*"{module_name}"(?P<body>.*?)\)'
)
VERSION_PATTERN = re.compile(r'\bversion\s*=\s*"(?P<version>[^"]+)"')
DEFAULT_MAX_COLLECTION_WORKERS = 8


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
    return snapshot_from_dict(raw)


def load_snapshot_if_present(path: Path) -> RepoSnapshot | None:
    if not path.exists():
        return None
    try:
        return load_snapshot(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def write_snapshot(snapshot: RepoSnapshot, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = snapshot_to_dict(snapshot)
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
        message = (
            f"Missing GitHub token. Set {token_env} or authenticate with `gh auth login`."
        )
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
    github_client: Any,
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
    organization: Organization,
    existing_snapshot: RepoSnapshot | None = None,
    *,
    status_prefix: str = "repo-overview",
) -> list[RepoEntry]:
    print_status("Loading active repositories", prefix=status_prefix)
    active_repositories = fetch_active_repositories(organization)
    print_status(
        f"Found {len(active_repositories)} active repositories",
        prefix=status_prefix,
    )
    print_status("Loading repository custom properties in bulk", prefix=status_prefix)
    custom_properties_by_name = fetch_repository_custom_properties(
        organization,
        active_repository_names=set(active_repositories),
    )
    print_status(
        f"Loaded custom properties for {len(custom_properties_by_name)} repositories",
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
    completion_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for index, (repository_name, repository) in enumerate(
            sorted_repositories,
            start=1,
        ):
            cached_entry = cached_by_name.get(repository_name)
            progress_note = (
                "using cached content signals"
                if cached_entry
                else "fetching content signals"
            )
            print_status(
                f"[{index}/{total_repositories}] Collecting {repository_name} ({progress_note})",
                prefix=status_prefix,
            )
            future = executor.submit(
                collect_repository_entry,
                repository_name=repository_name,
                repository=repository,
                custom_properties=custom_properties_by_name.get(repository_name, {}),
                cached_entry=cached_entry,
                cached_schema_version=existing_snapshot.schema_version
                if existing_snapshot is not None
                else None,
            )
            futures[future] = (index, repository_name)

        for future in as_completed(futures):
            index, repository_name = futures[future]
            repos_by_index[index] = future.result()
            completion_count += 1
            print_status(
                f"[{completion_count}/{total_repositories}] Finished {repository_name}",
                prefix=status_prefix,
            )

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


def fetch_active_repositories(organization: Organization) -> dict[str, Any]:
    active_repositories: dict[str, Any] = {}
    for repository in organization.get_repos():
        if getattr(repository, "archived", False):
            continue
        repository_name = getattr(repository, "name", None)
        if not isinstance(repository_name, str):
            continue
        active_repositories[repository_name] = repository
    return active_repositories


def fetch_repository_descriptions(organization: Organization) -> dict[str, str | None]:
    return {
        name: cast("str | None", getattr(repository, "description", None))
        for name, repository in fetch_active_repositories(organization).items()
    }


def fetch_repository_custom_properties(
    organization: Organization,
    *,
    active_repository_names: set[str],
) -> dict[str, dict[str, CustomPropertyValue]]:
    try:
        property_values = organization.list_custom_property_values()
    except AttributeError:
        return {}

    properties_by_name: dict[str, dict[str, CustomPropertyValue]] = {}
    for repository_properties in property_values:
        repository_name = getattr(repository_properties, "repository_name", None)
        if repository_name not in active_repository_names:
            continue

        properties = getattr(repository_properties, "properties", None)
        if not isinstance(properties, dict):
            continue
        properties_by_name[repository_name] = cast(
            "dict[str, CustomPropertyValue]",
            properties,
        )

    return properties_by_name


def collect_repository_entry(
    *,
    repository_name: str,
    repository: Any,
    custom_properties: dict[str, CustomPropertyValue],
    cached_entry: RepoEntry | None,
    cached_schema_version: int | None = None,
) -> RepoEntry:
    default_branch = cast("str | None", getattr(repository, "default_branch", None))
    default_branch_sha = get_default_branch_sha(repository, default_branch)
    cached_content_signals = cached_signals_for_repository(
        cached_entry,
        cached_schema_version=cached_schema_version,
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
    )

    if cached_content_signals is None:
        content_signals = inspect_repository_content(
            repository,
            ref=default_branch_sha,
        )
    else:
        content_signals = cached_content_signals
    latest_release = get_latest_release_details(
        repository,
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
    )

    return build_repo_entry(
        repository_name=repository_name,
        description=cast("str | None", getattr(repository, "description", None)),
        custom_properties=custom_properties,
        default_branch=default_branch,
        default_branch_sha=default_branch_sha,
        last_push_date=iso_date(getattr(repository, "pushed_at", None)),
        open_issues=get_open_issue_count(repository),
        open_prs=get_open_pull_request_count(repository),
        bazel_version=content_signals["bazel_version"],
        docs_as_code_version=content_signals["docs_as_code_version"],
        has_lint_config=content_signals["has_lint_config"],
        has_ci=content_signals["has_ci"],
        uses_cicd_daily_workflow=content_signals["uses_cicd_daily_workflow"],
        has_coverage_config=content_signals["has_coverage_config"],
        latest_release_version=latest_release["version"],
        latest_release_date=latest_release["date"],
        commits_since_latest_release=latest_release["commits_since_release"],
        stars=getattr(repository, "stargazers_count", 0) or 0,
        forks=getattr(repository, "forks_count", 0) or 0,
    )


def cached_signals_for_repository(
    cached_entry: RepoEntry | None,
    *,
    cached_schema_version: int | None,
    default_branch: str | None,
    default_branch_sha: str | None,
) -> dict[str, str | bool | None] | None:
    if cached_entry is None:
        return None
    if cached_schema_version != SNAPSHOT_SCHEMA_VERSION:
        return None

    cached_sha = cached_entry.default_branch_sha
    if default_branch_sha is not None and cached_sha != default_branch_sha:
        return None

    if default_branch_sha is None and default_branch is not None and cached_entry.default_branch != default_branch:
        return None

    return {
        "bazel_version": cached_entry.bazel_version,
        "docs_as_code_version": cached_entry.docs_as_code_version,
        "has_lint_config": cached_entry.has_lint_config,
        "has_ci": cached_entry.has_ci,
        "uses_cicd_daily_workflow": cached_entry.uses_cicd_daily_workflow,
        "has_coverage_config": cached_entry.has_coverage_config,
    }


def build_repo_entry(
    repository_name: str,
    description: str | None,
    custom_properties: dict[str, CustomPropertyValue],
    *,
    default_branch: str | None = None,
    default_branch_sha: str | None = None,
    last_push_date: str | None = None,
    open_issues: int = 0,
    open_prs: int = 0,
    bazel_version: str | None = None,
    docs_as_code_version: str | None = None,
    has_lint_config: bool = False,
    has_ci: bool = False,
    uses_cicd_daily_workflow: bool = False,
    has_coverage_config: bool = False,
    latest_release_version: str | None = None,
    latest_release_date: str | None = None,
    commits_since_latest_release: int | None = None,
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
        last_push_date=last_push_date,
        open_issues=open_issues,
        open_prs=open_prs,
        bazel_version=bazel_version,
        docs_as_code_version=docs_as_code_version,
        has_lint_config=has_lint_config,
        has_ci=has_ci,
        uses_cicd_daily_workflow=uses_cicd_daily_workflow,
        has_coverage_config=has_coverage_config,
        latest_release_version=latest_release_version,
        latest_release_date=latest_release_date,
        commits_since_latest_release=commits_since_latest_release,
        stars=stars,
        forks=forks,
    )


def normalize_group_name(value: str | list[str] | None, fallback: str) -> str:
    if value is None:
        return fallback
    if isinstance(value, list):
        cleaned = [item.strip() for item in value if item.strip()]
        return ", ".join(cleaned) if cleaned else fallback
    cleaned = value.strip()
    return cleaned or fallback


def inspect_repository_content(
    repository: Any,
    *,
    ref: str | None,
) -> dict[str, str | bool | None]:
    tree_paths = fetch_repository_tree_paths(repository, ref=ref)
    if not tree_paths:
        return default_content_signals()

    return {
        "bazel_version": detect_bazel_version(
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


def default_content_signals() -> dict[str, str | bool | None]:
    return {
        "bazel_version": None,
        "docs_as_code_version": None,
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


def get_open_issue_count(repository: Any) -> int:
    count = getattr(repository, "open_issues_count", 0)
    return count if isinstance(count, int) else 0


def get_open_pull_request_count(repository: Any) -> int:
    if not hasattr(repository, "get_pulls"):
        return 0
    try:
        pulls = repository.get_pulls(state="open")
    except Exception:
        return 0
    total_count = getattr(pulls, "totalCount", 0)
    return total_count if isinstance(total_count, int) else 0


def get_latest_release_details(
    repository: Any,
    *,
    default_branch: str | None,
    default_branch_sha: str | None,
) -> dict[str, str | int | None]:
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


def default_latest_release_details() -> dict[str, str | int | None]:
    return {
        "version": None,
        "date": None,
        "commits_since_release": None,
    }


def get_latest_release_version(release: Any) -> str | None:
    try:
        raw_data = getattr(release, "raw_data", None)
    except Exception:
        raw_data = None
    if isinstance(raw_data, dict):
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


def get_release_date(release: Any) -> str | None:
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
    if value is None or not hasattr(value, "date"):
        return None
    return value.date().isoformat()
