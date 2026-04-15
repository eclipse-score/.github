from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

DEFAULT_CATEGORY = "Uncategorized"
DEFAULT_SUBCATEGORY = "General"
SNAPSHOT_SCHEMA_VERSION = 9
SUPPORTED_SNAPSHOT_SCHEMA_VERSIONS = frozenset({2, 3, 4, 5, 6, 7, 8, 9})


@dataclass(frozen=True, slots=True)
class RepoEntry:
    name: str
    description: str
    category: str
    subcategory: str
    default_branch: str | None = None
    default_branch_sha: str | None = None
    last_push_date: str | None = None
    open_issues: int = 0
    open_prs: int = 0
    open_ready_prs: int = 0
    open_draft_prs: int = 0
    is_bazel_repo: bool = False
    bazel_version: str | None = None
    codeowners: tuple[str, ...] = ()
    maintainers_in_bazel_registry: tuple[str, ...] = ()
    latest_bazel_registry_version: str | None = None
    docs_as_code_version: str | None = None
    has_lint_config: bool = False
    has_gitlint_config: bool = False
    has_pyproject_toml: bool = False
    has_pre_commit_config: bool = False
    has_ci: bool = False
    uses_cicd_daily_workflow: bool = False
    has_coverage_config: bool = False
    latest_release_version: str | None = None
    latest_release_date: str | None = None
    commits_since_latest_release: int | None = None
    stars: int = 0
    forks: int = 0


@dataclass(frozen=True, slots=True)
class SubcategoryConfig:
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class CategoryConfig:
    name: str
    description: str
    subcategories: tuple[SubcategoryConfig, ...] = ()


@dataclass(frozen=True, slots=True)
class ReadmeConfig:
    categories: tuple[CategoryConfig, ...]


@dataclass(frozen=True, slots=True)
class RepoSnapshot:
    schema_version: int
    org_name: str
    generated_at: str
    repos: tuple[RepoEntry, ...]


CustomPropertyValue = str | list[str] | None


def repo_entry_from_dict(
    data: Mapping[str, Any],
    *,
    snapshot_schema_version: int,
) -> RepoEntry:
    field_names = {field.name for field in fields(RepoEntry)}
    kwargs = {name: data[name] for name in field_names if name in data}
    for sequence_field in (
        "codeowners",
        "maintainers_in_bazel_registry",
    ):
        value = kwargs.get(sequence_field)
        if isinstance(value, list):
            kwargs[sequence_field] = tuple(
                item for item in value if isinstance(item, str)
            )
    if "latest_bazel_registry_version" not in kwargs:
        raw_versions = data.get("bazel_registry_versions")
        if isinstance(raw_versions, list):
            for raw_version in raw_versions:
                if isinstance(raw_version, str) and raw_version.strip():
                    kwargs["latest_bazel_registry_version"] = raw_version.strip()
                    break
    if snapshot_schema_version < 7:
        total_open_prs = kwargs.get("open_prs")
        if isinstance(total_open_prs, int):
            kwargs.setdefault("open_ready_prs", total_open_prs)
            kwargs.setdefault("open_draft_prs", 0)
            raw_open_issues = kwargs.get("open_issues")
            if isinstance(raw_open_issues, int):
                kwargs["open_issues"] = max(raw_open_issues - total_open_prs, 0)
    if snapshot_schema_version < 8 and "is_bazel_repo" not in kwargs:
        kwargs["is_bazel_repo"] = any(
            [
                isinstance(kwargs.get("bazel_version"), str)
                and bool(kwargs["bazel_version"].strip()),
                isinstance(kwargs.get("docs_as_code_version"), str)
                and bool(kwargs["docs_as_code_version"].strip()),
                isinstance(kwargs.get("latest_bazel_registry_version"), str)
                and bool(kwargs["latest_bazel_registry_version"].strip()),
            ]
        )
    return RepoEntry(**kwargs)


def snapshot_from_dict(data: Mapping[str, Any]) -> RepoSnapshot:
    repos_data = data.get("repos")
    if not isinstance(repos_data, list):
        raise ValueError("Snapshot payload must contain a 'repos' list.")

    schema_version = data.get("schema_version", SNAPSHOT_SCHEMA_VERSION)
    if schema_version not in SUPPORTED_SNAPSHOT_SCHEMA_VERSIONS:
        raise ValueError(
            "Unsupported snapshot schema version "
            f"{schema_version}; expected one of "
            f"{sorted(SUPPORTED_SNAPSHOT_SCHEMA_VERSIONS)}."
        )

    org_name = data.get("org_name")
    generated_at = data.get("generated_at")
    if not isinstance(org_name, str) or not org_name:
        raise ValueError("Snapshot payload must contain a non-empty 'org_name'.")
    if not isinstance(generated_at, str) or not generated_at:
        raise ValueError("Snapshot payload must contain a non-empty 'generated_at'.")

    return RepoSnapshot(
        schema_version=schema_version,
        org_name=org_name,
        generated_at=generated_at,
        repos=tuple(
            repo_entry_from_dict(
                repo,
                snapshot_schema_version=schema_version,
            )
            for repo in repos_data
        ),
    )


def snapshot_to_dict(snapshot: RepoSnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version,
        "org_name": snapshot.org_name,
        "generated_at": snapshot.generated_at,
        "repos": [asdict(repo) for repo in snapshot.repos],
    }
