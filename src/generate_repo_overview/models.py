from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

DEFAULT_CATEGORY = "Uncategorized"
DEFAULT_SUBCATEGORY = "General"
SNAPSHOT_SCHEMA_VERSION = 10


@dataclass(frozen=True, slots=True)
class DeepContentSignals:
    """Deep, slow-to-collect content signals from default-branch tree inspection."""

    is_bazel_repo: bool = False
    bazel_version: str | None = None
    codeowners: tuple[str, ...] = ()
    docs_as_code_version: str | None = None
    has_lint_config: bool = False
    has_gitlint_config: bool = False
    has_pyproject_toml: bool = False
    has_pre_commit_config: bool = False
    has_ci: bool = False
    uses_cicd_daily_workflow: bool = False
    has_coverage_config: bool = False

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DeepContentSignals:
        return cls(
            is_bazel_repo=bool(data.get("is_bazel_repo", False)),
            bazel_version=cast("str | None", data.get("bazel_version")),
            codeowners=normalize_string_tuple(data.get("codeowners")),
            docs_as_code_version=cast("str | None", data.get("docs_as_code_version")),
            has_lint_config=bool(data.get("has_lint_config", False)),
            has_gitlint_config=bool(data.get("has_gitlint_config", False)),
            has_pyproject_toml=bool(data.get("has_pyproject_toml", False)),
            has_pre_commit_config=bool(data.get("has_pre_commit_config", False)),
            has_ci=bool(data.get("has_ci", False)),
            uses_cicd_daily_workflow=bool(data.get("uses_cicd_daily_workflow", False)),
            has_coverage_config=bool(data.get("has_coverage_config", False)),
        )


@dataclass(frozen=True, slots=True)
class RegistrySignals:
    """Registry-sourced signals collected from shared bazel registry metadata."""

    maintainers_in_bazel_registry: tuple[str, ...] = ()
    latest_bazel_registry_version: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RegistrySignals:
        return cls(
            maintainers_in_bazel_registry=normalize_string_tuple(
                data.get("maintainers_in_bazel_registry")
            ),
            latest_bazel_registry_version=cast(
                "str | None",
                data.get("latest_bazel_registry_version"),
            ),
        )


@dataclass(frozen=True, slots=True)
class VolatileMetricsSnapshot:
    """Fast-refresh volatile activity metrics with optional fetch timestamp."""

    last_push_date: str | None = None
    merged_prs_30_days: int = 0
    open_issues: int = 0
    open_prs: int = 0
    open_ready_prs: int = 0
    open_draft_prs: int = 0
    latest_release_version: str | None = None
    latest_release_date: str | None = None
    commits_since_latest_release: int | None = None
    volatile_metrics_fetched_at: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> VolatileMetricsSnapshot:
        return cls(
            last_push_date=cast("str | None", data.get("last_push_date")),
            merged_prs_30_days=cast("int", data.get("merged_prs_30_days", 0)),
            open_issues=cast("int", data.get("open_issues", 0)),
            open_prs=cast("int", data.get("open_prs", 0)),
            open_ready_prs=cast("int", data.get("open_ready_prs", 0)),
            open_draft_prs=cast("int", data.get("open_draft_prs", 0)),
            latest_release_version=cast("str | None", data.get("latest_release_version")),
            latest_release_date=cast("str | None", data.get("latest_release_date")),
            commits_since_latest_release=cast(
                "int | None",
                data.get("commits_since_latest_release"),
            ),
            volatile_metrics_fetched_at=cast(
                "str | None",
                data.get("volatile_metrics_fetched_at"),
            ),
        )


@dataclass(frozen=True, slots=True)
class RepoEntry:
    """Normalized repository record grouped by collection cadence and source."""

    name: str
    description: str
    category: str
    subcategory: str
    default_branch: str | None = None
    default_branch_sha: str | None = None
    content: DeepContentSignals = field(default_factory=DeepContentSignals)
    registry: RegistrySignals = field(default_factory=RegistrySignals)
    volatile: VolatileMetricsSnapshot = field(default_factory=VolatileMetricsSnapshot)
    stars: int = 0
    forks: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RepoEntry:
        content_payload = cast("Mapping[str, Any]", data.get("content", {}))
        registry_payload = cast("Mapping[str, Any]", data.get("registry", {}))
        volatile_payload = cast("Mapping[str, Any]", data.get("volatile", {}))

        return cls(
            name=cast("str", data.get("name", "")),
            description=cast("str", data.get("description", "(no description)")),
            category=cast("str", data.get("category", DEFAULT_CATEGORY)),
            subcategory=cast("str", data.get("subcategory", DEFAULT_SUBCATEGORY)),
            default_branch=cast("str | None", data.get("default_branch")),
            default_branch_sha=cast("str | None", data.get("default_branch_sha")),
            content=DeepContentSignals.from_dict(content_payload),
            registry=RegistrySignals.from_dict(registry_payload),
            volatile=VolatileMetricsSnapshot.from_dict(volatile_payload),
            stars=cast("int", data.get("stars", 0)),
            forks=cast("int", data.get("forks", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return cast("dict[str, Any]", asdict(self))


@dataclass(frozen=True, slots=True)
class SubcategoryConfig:
    """Rendering configuration for a subcategory section in the profile README."""

    name: str
    description: str


@dataclass(frozen=True, slots=True)
class CategoryConfig:
    """Rendering configuration for a category and its subcategory ordering."""

    name: str
    description: str
    subcategories: tuple[SubcategoryConfig, ...] = ()


@dataclass(frozen=True, slots=True)
class ReadmeConfig:
    """Top-level rendering configuration for grouping repositories in README output."""

    categories: tuple[CategoryConfig, ...]


@dataclass(frozen=True, slots=True)
class RepoSnapshot:
    """Versioned snapshot payload containing all normalized repository entries."""

    schema_version: int
    org_name: str
    generated_at: str
    repos: tuple[RepoEntry, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RepoSnapshot:
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

        return cls(
            schema_version=cast("int", schema_version),
            org_name=org_name,
            generated_at=generated_at,
            repos=tuple(RepoEntry.from_dict(repo) for repo in typed_repos_data),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "org_name": self.org_name,
            "generated_at": self.generated_at,
            "repos": [repo.to_dict() for repo in self.repos],
        }


CustomPropertyValue = str | list[str] | None


def normalize_string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, tuple):
        return tuple(item for item in value if isinstance(item, str))
    if isinstance(value, list):
        sequence_items = cast("list[object]", value)
        return tuple(item for item in sequence_items if isinstance(item, str))
    return ()
