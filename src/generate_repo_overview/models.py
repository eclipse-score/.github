from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

DEFAULT_CATEGORY = "Uncategorized"
DEFAULT_SUBCATEGORY = "General"
SNAPSHOT_SCHEMA_VERSION = 9


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


def normalize_sequence_fields(kwargs: dict[str, Any]) -> None:
    for sequence_field in (
        "codeowners",
        "maintainers_in_bazel_registry",
    ):
        value = kwargs.get(sequence_field)
        if isinstance(value, list):
            sequence_items = cast("list[object]", value)
            kwargs[sequence_field] = tuple(
                item for item in sequence_items if isinstance(item, str)
            )


def repo_entry_from_dict(
    data: Mapping[str, Any],
) -> RepoEntry:
    field_names = {field.name for field in fields(RepoEntry)}
    kwargs = {name: data[name] for name in field_names if name in data}
    normalize_sequence_fields(kwargs)
    return RepoEntry(**kwargs)


def snapshot_from_dict(data: Mapping[str, Any]) -> RepoSnapshot:
    repos_data = data.get("repos")
    if not isinstance(repos_data, list):
        raise ValueError("Snapshot payload must contain a 'repos' list.")

    schema_version = data.get("schema_version", SNAPSHOT_SCHEMA_VERSION)
    if schema_version != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported snapshot schema version "
            f"{schema_version}; expected {SNAPSHOT_SCHEMA_VERSION}."
        )

    org_name = data.get("org_name")
    generated_at = data.get("generated_at")
    if not isinstance(org_name, str) or not org_name:
        raise ValueError("Snapshot payload must contain a non-empty 'org_name'.")
    if not isinstance(generated_at, str) or not generated_at:
        raise ValueError("Snapshot payload must contain a non-empty 'generated_at'.")

    typed_repos_data = cast("list[Mapping[str, Any]]", repos_data)

    return RepoSnapshot(
        schema_version=schema_version,
        org_name=org_name,
        generated_at=generated_at,
        repos=tuple(repo_entry_from_dict(repo) for repo in typed_repos_data),
    )


def snapshot_to_dict(snapshot: RepoSnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version,
        "org_name": snapshot.org_name,
        "generated_at": snapshot.generated_at,
        "repos": [asdict(repo) for repo in snapshot.repos],
    }
