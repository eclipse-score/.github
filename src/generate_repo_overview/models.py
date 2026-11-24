from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, cast
from urllib.parse import urlsplit


class LockfileStatus(StrEnum):
    OK = "ok"
    MISSING = "missing"
    ERROR = "error"
    TIMEOUT = "timeout"
    # The organization does not run repository tools, so nothing was checked.
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


DEFAULT_CATEGORY = "Uncategorized"
DEFAULT_SUBCATEGORY = "General"
SNAPSHOT_SCHEMA_VERSION = 35
_LEGACY_SNAPSHOT_SCHEMA_VERSIONS = (30, 31, 32, 33, 34)


@dataclass(frozen=True, slots=True)
class GroupingLevel:
    """A grouping dimension mapped to a GitHub custom property key."""

    property: str
    default: str


@dataclass(frozen=True, slots=True)
class TrackedDep:
    """A Bazel dependency tracked across all repositories."""

    repo: str
    module_name: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TrackedDep:
        return cls(
            repo=cast("str", data.get("repo", "")),
            module_name=cast("str", data.get("module_name", "")),
        )

    def to_dict(self) -> dict[str, str]:
        return {"repo": self.repo, "module_name": self.module_name}


@dataclass(frozen=True, slots=True)
class WorkflowSignal:
    """A named workflow signal with a reference string to match."""

    label: str
    reference: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WorkflowSignal:
        return cls(
            label=cast("str", data.get("label", "")),
            reference=cast("str", data.get("reference", "")),
        )

    def to_dict(self) -> dict[str, str]:
        return {"label": self.label, "reference": self.reference}


@dataclass(frozen=True, slots=True)
class WorkflowRefResolution:
    """Release context for one full workflow reference, refreshed each collection."""

    reference: str
    resolved_sha: str | None = None
    version_tag: str | None = None
    latest_release: str | None = None
    ahead_by: int | None = None
    behind_by: int | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WorkflowRefResolution:
        return cls(
            reference=cast("str", data.get("reference", "")),
            resolved_sha=cast("str | None", data.get("resolved_sha")),
            version_tag=cast("str | None", data.get("version_tag")),
            latest_release=cast("str | None", data.get("latest_release")),
            ahead_by=cast("int | None", data.get("ahead_by")),
            behind_by=cast("int | None", data.get("behind_by")),
        )


class DependencyOverride(StrEnum):
    GIT = "git"
    ARCHIVE = "archive"
    LOCAL_PATH = "local_path"
    SINGLE_VERSION = "single_version"


class DependencyPinKind(StrEnum):
    VERSION = "version"
    COMMIT = "commit"
    TAG = "tag"
    BRANCH = "branch"


@dataclass(frozen=True, slots=True)
class DependencyDeclaration:
    """One direct ``bazel_dep`` declaration and its root module override."""

    module: str
    version: str | None = None
    override: DependencyOverride | None = None
    remote: str | None = None
    revision: str | None = None
    pin_kind: DependencyPinKind = DependencyPinKind.VERSION
    override_source: tuple[tuple[str, str], ...] = ()
    # None selects the configured registry. An empty string means the override
    # specified a registry expression that could not be evaluated.
    registry_override: str | None = None

    @property
    def pinned_revision(self) -> str | None:
        """The declared commit, tag, branch, or module version.

        A ``git_override`` replaces the declared version. Archive and local-path
        overrides have no revision in the dependency's Git history.
        """
        if self.override is DependencyOverride.GIT:
            return self.revision
        if self.override in (DependencyOverride.ARCHIVE, DependencyOverride.LOCAL_PATH):
            return None
        return self.version

    @property
    def display_version(self) -> str:
        """The declared version or Git revision, shortened for display."""
        if self.override is DependencyOverride.GIT:
            if self.revision and self.pin_kind is DependencyPinKind.COMMIT:
                return short_revision(self.revision)
            return self.revision or "unknown"
        if self.override in (DependencyOverride.ARCHIVE, DependencyOverride.LOCAL_PATH):
            return "unknown"
        return self.version or (
            "unknown"
            if self.override is DependencyOverride.SINGLE_VERSION
            else "unversioned"
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DependencyDeclaration:
        override = data.get("override")
        return cls(
            module=cast("str", data.get("module", "")),
            version=cast("str | None", data.get("version")),
            override=DependencyOverride(override)
            if override in DependencyOverride
            else None,
            remote=cast("str | None", data.get("remote")),
            revision=cast("str | None", data.get("revision")),
            pin_kind=DependencyPinKind(data.get("pin_kind", DependencyPinKind.VERSION)),
            override_source=normalize_string_pairs(data.get("override_source")),
            registry_override=cast("str | None", data.get("registry_override")),
        )


@dataclass(frozen=True, slots=True)
class DependencyResolution:
    """Freshness of a declared pin relative to releases and the default branch."""

    repository: str
    revision: str
    resolved_sha: str | None = None
    latest_release: str | None = None
    behind_latest_release_by: int | None = None
    ahead_of_default_branch_by: int | None = None
    behind_default_branch_by: int | None = None
    pin_kind: DependencyPinKind = DependencyPinKind.VERSION
    consumer_org: str = field(kw_only=True)
    module: str = field(kw_only=True)
    registry_override: str | None = field(default=None, kw_only=True)
    registry_update_available: bool | None = field(default=None, kw_only=True)

    @property
    def release_update_available(self) -> bool | None:
        """Whether there is a newer module package or a Git release to catch up to."""
        if self.latest_release is None:
            return None
        if self.registry_update_available is not None:
            return self.registry_update_available
        if self.behind_latest_release_by is not None:
            return self.behind_latest_release_by > 0
        return None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DependencyResolution:
        return cls(
            repository=cast("str", data.get("repository", "")),
            revision=cast("str", data.get("revision", "")),
            resolved_sha=cast("str | None", data.get("resolved_sha")),
            latest_release=cast("str | None", data.get("latest_release")),
            behind_latest_release_by=cast(
                "int | None", data.get("behind_latest_release_by")
            ),
            ahead_of_default_branch_by=cast(
                "int | None", data.get("ahead_of_default_branch_by")
            ),
            behind_default_branch_by=cast(
                "int | None", data.get("behind_default_branch_by")
            ),
            pin_kind=DependencyPinKind(data.get("pin_kind", DependencyPinKind.VERSION)),
            consumer_org=cast("str", data.get("consumer_org", "")),
            module=cast("str", data.get("module", "")),
            registry_override=cast("str | None", data.get("registry_override")),
            registry_update_available=cast(
                "bool | None", data.get("registry_update_available")
            ),
        )


@dataclass(frozen=True, slots=True)
class SphinxItem:
    """A feature or module declared in the platform Sphinx documentation."""

    path: str
    title: str
    identifier: str
    source_repo: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SphinxItem:
        return cls(
            path=cast("str", data.get("path", "")),
            title=cast("str", data.get("title", "")),
            identifier=cast("str", data.get("identifier", "")),
            source_repo=cast("str", data.get("source_repo", "")),
        )


@dataclass(frozen=True, slots=True)
class DeepContentSignals:
    """Deep, slow-to-collect content signals from default-branch tree inspection."""

    is_bazel_repo: bool = False
    has_bazel_module: bool = False
    bazel_module_name: str | None = None
    bazel_version: str | None = None
    codeowners: tuple[str, ...] = ()
    referenced_by_reference_integration: bool = False
    reference_integration_module: str | None = None
    reference_integration_group: str | None = None
    reference_integration_branch: str | None = None
    reference_integration_version: str | None = None
    reference_integration_hash: str | None = None
    reference_integration_resolved_hash: str | None = None
    reference_integration_release_ahead_of_main_by: int | None = None
    reference_integration_main_ahead_of_release_by: int | None = None
    reference_integration_pin_ahead_of_main_by: int | None = None
    reference_integration_main_ahead_of_pin_by: int | None = None
    has_lint_config: bool = False
    has_gitlint_config: bool = False
    has_pyproject_toml: bool = False
    has_pre_commit_config: bool = False
    has_ci: bool = False
    matched_workflow_signals: tuple[str, ...] = ()
    workflow_refs: tuple[tuple[str, str], ...] = ()
    has_coverage_config: bool = False
    top_languages: tuple[str, ...] = ()
    bazel_deps: tuple[DependencyDeclaration, ...] = ()
    bazel_lockfile_status: LockfileStatus = LockfileStatus.UNKNOWN
    bazel_lockfile_error_output: str | None = None
    sphinx_features: tuple[SphinxItem, ...] = ()
    sphinx_modules: tuple[SphinxItem, ...] = ()
    docs_feature_paths: tuple[str, ...] = ()
    repo_sphinx_features: tuple[SphinxItem, ...] = ()
    repo_sphinx_modules: tuple[SphinxItem, ...] = ()
    sphinx_project_name: str | None = None
    sphinx_project_prefix: str | None = None
    has_dependabot_config: bool | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DeepContentSignals:
        return cls(
            is_bazel_repo=bool(data.get("is_bazel_repo", False)),
            has_bazel_module=bool(data.get("has_bazel_module", False)),
            bazel_module_name=cast("str | None", data.get("bazel_module_name")),
            bazel_version=cast("str | None", data.get("bazel_version")),
            codeowners=normalize_string_tuple(data.get("codeowners")),
            referenced_by_reference_integration=bool(
                data.get("referenced_by_reference_integration", False)
            ),
            reference_integration_module=cast(
                "str | None", data.get("reference_integration_module")
            ),
            reference_integration_group=cast(
                "str | None", data.get("reference_integration_group")
            ),
            reference_integration_branch=cast(
                "str | None", data.get("reference_integration_branch")
            ),
            reference_integration_version=cast(
                "str | None", data.get("reference_integration_version")
            ),
            reference_integration_hash=cast(
                "str | None", data.get("reference_integration_hash")
            ),
            reference_integration_resolved_hash=cast(
                "str | None", data.get("reference_integration_resolved_hash")
            ),
            reference_integration_release_ahead_of_main_by=cast(
                "int | None", data.get("reference_integration_release_ahead_of_main_by")
            ),
            reference_integration_main_ahead_of_release_by=cast(
                "int | None", data.get("reference_integration_main_ahead_of_release_by")
            ),
            reference_integration_pin_ahead_of_main_by=cast(
                "int | None", data.get("reference_integration_pin_ahead_of_main_by")
            ),
            reference_integration_main_ahead_of_pin_by=cast(
                "int | None", data.get("reference_integration_main_ahead_of_pin_by")
            ),
            has_lint_config=bool(data.get("has_lint_config", False)),
            has_gitlint_config=bool(data.get("has_gitlint_config", False)),
            has_pyproject_toml=bool(data.get("has_pyproject_toml", False)),
            has_pre_commit_config=bool(data.get("has_pre_commit_config", False)),
            has_ci=bool(data.get("has_ci", False)),
            has_dependabot_config=cast(
                "bool | None", data.get("has_dependabot_config")
            ),
            matched_workflow_signals=normalize_string_tuple(
                data.get("matched_workflow_signals")
            ),
            workflow_refs=normalize_string_pairs(data.get("workflow_refs")),
            has_coverage_config=bool(data.get("has_coverage_config", False)),
            top_languages=normalize_string_tuple(data.get("top_languages")),
            bazel_deps=_parse_dependencies(data.get("bazel_deps")),
            bazel_lockfile_status=_parse_lockfile_status(
                data.get("bazel_lockfile_status")
            ),
            bazel_lockfile_error_output=cast(
                "str | None", data.get("bazel_lockfile_error_output")
            ),
            sphinx_features=_parse_sphinx_items(data.get("sphinx_features")),
            sphinx_modules=_parse_sphinx_items(data.get("sphinx_modules")),
            docs_feature_paths=normalize_string_tuple(data.get("docs_feature_paths")),
            repo_sphinx_features=_parse_sphinx_items(data.get("repo_sphinx_features")),
            repo_sphinx_modules=_parse_sphinx_items(data.get("repo_sphinx_modules")),
            sphinx_project_name=cast("str | None", data.get("sphinx_project_name")),
            sphinx_project_prefix=cast("str | None", data.get("sphinx_project_prefix")),
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
    latest_release_ahead_of_default_branch_by: int | None = None
    default_branch_ahead_of_latest_release_by: int | None = None
    release_bazel_version: str | None = None
    release_bazel_deps: tuple[DependencyDeclaration, ...] = ()
    volatile_metrics_fetched_at: str | None = None
    open_renovate_prs: int | None = None
    open_dependabot_prs: int | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> VolatileMetricsSnapshot:
        fetched_at = cast("str | None", data.get("volatile_metrics_fetched_at"))
        # Refresh activity metrics for snapshots from before bot PR counts were
        # collected. Explicit null counts are valid when GitHub is unavailable.
        if "open_renovate_prs" not in data or "open_dependabot_prs" not in data:
            fetched_at = None
        return cls(
            last_push_date=cast("str | None", data.get("last_push_date")),
            merged_prs_30_days=cast("int", data.get("merged_prs_30_days", 0)),
            open_issues=cast("int", data.get("open_issues", 0)),
            open_prs=cast("int", data.get("open_prs", 0)),
            open_ready_prs=cast("int", data.get("open_ready_prs", 0)),
            open_draft_prs=cast("int", data.get("open_draft_prs", 0)),
            open_renovate_prs=cast("int | None", data.get("open_renovate_prs")),
            open_dependabot_prs=cast("int | None", data.get("open_dependabot_prs")),
            latest_release_version=cast(
                "str | None", data.get("latest_release_version")
            ),
            latest_release_date=cast("str | None", data.get("latest_release_date")),
            commits_since_latest_release=cast(
                "int | None",
                data.get("commits_since_latest_release"),
            ),
            latest_release_ahead_of_default_branch_by=cast(
                "int | None", data.get("latest_release_ahead_of_default_branch_by")
            ),
            default_branch_ahead_of_latest_release_by=cast(
                "int | None", data.get("default_branch_ahead_of_latest_release_by")
            ),
            release_bazel_version=cast(
                "str | None",
                data.get("release_bazel_version"),
            ),
            release_bazel_deps=_parse_dependencies(data.get("release_bazel_deps")),
            volatile_metrics_fetched_at=fetched_at,
        )


@dataclass(frozen=True, slots=True)
class TraceabilityTypeMetrics:
    """Parsed traceability metrics for one requirement type within a repository."""

    type_name: str
    req_total: int = 0
    req_with_code_link: int = 0
    req_with_test_link: int = 0
    req_fully_linked: int = 0
    tests_total: int = 0
    tests_linked: int = 0

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TraceabilityTypeMetrics:
        return cls(
            type_name=cast("str", data.get("type_name", "")),
            req_total=cast("int", data.get("req_total", 0)),
            req_with_code_link=cast("int", data.get("req_with_code_link", 0)),
            req_with_test_link=cast("int", data.get("req_with_test_link", 0)),
            req_fully_linked=cast("int", data.get("req_fully_linked", 0)),
            tests_total=cast("int", data.get("tests_total", 0)),
            tests_linked=cast("int", data.get("tests_linked", 0)),
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
    traceability: tuple[TraceabilityTypeMetrics, ...] = ()

    owner: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}" if self.owner else self.name

    def validate_path_segments(self, default_owner: str = "") -> None:
        # Snapshots can be loaded from disk. Each name must be a single GitHub path segment.
        owner = self.owner or default_owner
        parts = (owner, self.name) if owner else (self.name,)
        if any(
            part in {".", ".."} or not re.fullmatch(r"[a-zA-Z0-9_.-]+", part)
            for part in parts
        ):
            raise ValueError(f"Invalid repository name in snapshot: {self.full_name!r}")

    def detail_path(self, primary_org: str) -> str:
        self.validate_path_segments(primary_org)
        if self.owner and self.owner.casefold() != primary_org.casefold():
            # The @ prefix reserves a namespace outside the GitHub repository name alphabet.
            return f"@orgs/{self.full_name}/index.html"
        return f"{self.name}/index.html"

    def matches_repository(self, repository: str) -> bool:
        identity = repository if self.owner else repository.rsplit("/", 1)[-1]
        return self.full_name.casefold() == identity.casefold()

    @classmethod
    def from_dict(
        cls, data: Mapping[str, Any], *, default_owner: str = ""
    ) -> RepoEntry:
        content_payload = cast("Mapping[str, Any]", data.get("content", {}))
        registry_payload = cast("Mapping[str, Any]", data.get("registry", {}))
        volatile_payload = cast("Mapping[str, Any]", data.get("volatile", {}))
        traceability_payload = data.get("traceability", ())

        return cls(
            name=cast("str", data.get("name", "")),
            owner=cast("str", data.get("owner") or default_owner),
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
            traceability=tuple(
                TraceabilityTypeMetrics.from_dict(cast("Mapping[str, Any]", item))
                for item in traceability_payload
            )
            if isinstance(traceability_payload, (list, tuple))
            else (),
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
    tracked_deps: tuple[TrackedDep, ...] = ()
    workflow_signals: tuple[WorkflowSignal, ...] = ()
    workflow_ref_resolutions: tuple[WorkflowRefResolution, ...] = ()
    additional_org_names: tuple[str, ...] = ()
    module_repositories: Mapping[str, Mapping[str, str]] = field(
        default_factory=dict[str, Mapping[str, str]]
    )
    dependency_resolutions: tuple[DependencyResolution, ...] = ()
    dependency_sources_available: bool = True
    _dependency_resolutions_by_pin: dict[
        tuple[str, str, DependencyPinKind, str, str, str | None], DependencyResolution
    ] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_dependency_resolutions_by_pin",
            {
                (
                    resolution.consumer_org.casefold(),
                    resolution.module,
                    resolution.pin_kind,
                    resolution.revision,
                    resolution.repository.casefold()
                    if resolution.pin_kind is not DependencyPinKind.VERSION
                    else "",
                    resolution.registry_override,
                ): resolution
                for resolution in self.dependency_resolutions
            },
        )

    @property
    def organization_names(self) -> tuple[str, ...]:
        return (self.org_name, *self.additional_org_names)

    def dependency_repository(
        self, consumer: RepoEntry, declaration: DependencyDeclaration
    ) -> str | None:
        resolution = self.dependency_resolution(consumer, declaration)
        if resolution is not None:
            return resolution.repository
        if declaration.pinned_revision is not None:
            # For a versioned pin, the module-wide mapping may point to a
            # different registry's source. Git remotes identify their own source.
            return dependency_repository(declaration, {})
        owner = (consumer.owner or self.org_name).casefold()
        return dependency_repository(
            declaration, self.module_repositories.get(owner, {})
        )

    def dependency_resolution(
        self, consumer: RepoEntry, declaration: DependencyDeclaration
    ) -> DependencyResolution | None:
        revision = declaration.pinned_revision
        if revision is None:
            return None
        repository = (
            dependency_repository(declaration, {})
            if declaration.override is DependencyOverride.GIT
            else None
        )
        return self._dependency_resolutions_by_pin.get(
            (
                (consumer.owner or self.org_name).casefold(),
                declaration.module,
                declaration.pin_kind,
                revision,
                (repository or "").casefold(),
                declaration.registry_override,
            )
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RepoSnapshot:
        repos_data = data.get("repos")
        if not isinstance(repos_data, list):
            raise ValueError("Snapshot payload must contain a 'repos' list.")

        schema_version = data.get("schema_version", SNAPSHOT_SCHEMA_VERSION)
        if schema_version not in (
            SNAPSHOT_SCHEMA_VERSION,
            *_LEGACY_SNAPSHOT_SCHEMA_VERSIONS,
        ):
            raise ValueError(
                "Unsupported snapshot schema version "
                f"{schema_version}; expected {SNAPSHOT_SCHEMA_VERSION}."
            )

        org_name = data.get("org_name")
        generated_at = data.get("generated_at")
        if not isinstance(org_name, str) or not org_name:
            raise ValueError("Snapshot payload must contain a non-empty 'org_name'.")
        if not isinstance(generated_at, str) or not generated_at:
            raise ValueError(
                "Snapshot payload must contain a non-empty 'generated_at'."
            )

        typed_repos_data = cast("list[Mapping[str, Any]]", repos_data)
        dependency_sources_available = (
            schema_version == SNAPSHOT_SCHEMA_VERSION
            and data.get("dependency_sources_available", True) is True
        )

        tracked_deps = tuple(
            TrackedDep.from_dict(cast("Mapping[str, Any]", item))
            for item in (data.get("tracked_deps") or ())
            if isinstance(item, dict)
            and isinstance(item.get("repo"), str)
            and item["repo"]
            and isinstance(item.get("module_name"), str)
            and item["module_name"]
        )
        workflow_signals = tuple(
            WorkflowSignal.from_dict(cast("Mapping[str, Any]", item))
            for item in (data.get("workflow_signals") or ())
            if isinstance(item, dict)
            and isinstance(item.get("label"), str)
            and item["label"]
            and isinstance(item.get("reference"), str)
            and item["reference"]
        )

        return cls(
            schema_version=SNAPSHOT_SCHEMA_VERSION,
            org_name=org_name,
            generated_at=generated_at,
            repos=tuple(
                RepoEntry.from_dict(
                    repo, default_owner=org_name if schema_version == 30 else ""
                )
                for repo in typed_repos_data
            ),
            additional_org_names=normalize_string_tuple(
                data.get("additional_org_names")
            ),
            tracked_deps=tracked_deps,
            workflow_signals=workflow_signals,
            workflow_ref_resolutions=tuple(
                WorkflowRefResolution.from_dict(cast("Mapping[str, Any]", item))
                for item in (data.get("workflow_ref_resolutions") or ())
                if isinstance(item, dict) and isinstance(item.get("reference"), str)
            ),
            module_repositories=_parse_module_repositories(
                data.get("module_repositories")
                if dependency_sources_available
                else None
            ),
            dependency_resolutions=tuple(
                DependencyResolution.from_dict(cast("Mapping[str, Any]", item))
                for item in (data.get("dependency_resolutions") or ())
                if dependency_sources_available
                and isinstance(item, dict)
                and isinstance(item.get("repository"), str)
                and isinstance(item.get("revision"), str)
                and isinstance(item.get("consumer_org"), str)
                and isinstance(item.get("module"), str)
            ),
            dependency_sources_available=dependency_sources_available,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "org_name": self.org_name,
            "additional_org_names": list(self.additional_org_names),
            "generated_at": self.generated_at,
            "repos": [repo.to_dict() for repo in self.repos],
            "tracked_deps": [dep.to_dict() for dep in self.tracked_deps],
            "workflow_signals": [s.to_dict() for s in self.workflow_signals],
            "workflow_ref_resolutions": [
                asdict(r) for r in self.workflow_ref_resolutions
            ],
            "module_repositories": {
                owner: dict(sorted(modules.items()))
                for owner, modules in sorted(self.module_repositories.items())
            },
            "dependency_resolutions": [asdict(r) for r in self.dependency_resolutions],
            "dependency_sources_available": self.dependency_sources_available,
        }


CustomPropertyValue = str | list[str] | None


def _parse_lockfile_status(value: object) -> LockfileStatus:
    if isinstance(value, str):
        try:
            return LockfileStatus(value)
        except ValueError:
            pass
    return LockfileStatus.UNKNOWN


def normalize_string_pairs(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    items = cast("list[object]", list(value))
    result: list[tuple[str, str]] = []
    for raw in items:
        pair = (
            cast("list[object]", list(raw)) if isinstance(raw, (list, tuple)) else None
        )
        if pair is None or len(pair) != 2:
            continue
        name, ver = pair[0], pair[1]
        if isinstance(name, str) and isinstance(ver, str):
            result.append((name, ver))
    return tuple(result)


def normalize_string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, tuple):
        return tuple(item for item in value if isinstance(item, str))
    if isinstance(value, list):
        sequence_items = cast("list[object]", value)
        return tuple(item for item in sequence_items if isinstance(item, str))
    return ()


def _parse_sphinx_items(value: object) -> tuple[SphinxItem, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(
        SphinxItem.from_dict(cast("Mapping[str, Any]", item))
        for item in value
        if isinstance(item, dict)
    )


def _parse_dependencies(value: object) -> tuple[DependencyDeclaration, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    items = cast("tuple[object, ...]", tuple(value))
    declarations = tuple(
        DependencyDeclaration.from_dict(cast("Mapping[str, Any]", item))
        for item in items
        if isinstance(item, dict) and isinstance(item.get("module"), str)
    )
    legacy = tuple(
        DependencyDeclaration(module, version)
        for module, version in normalize_string_pairs(items)
    )
    return declarations + legacy


def _parse_module_repositories(value: object) -> dict[str, Mapping[str, str]]:
    if not isinstance(value, dict):
        return {}
    return {
        owner.casefold(): {
            module: repo
            for module, repo in cast("dict[object, object]", modules).items()
            if isinstance(module, str) and isinstance(repo, str)
        }
        for owner, modules in cast("dict[object, object]", value).items()
        if isinstance(owner, str) and isinstance(modules, dict)
    }


def dependency_repository(
    declaration: DependencyDeclaration,
    module_repositories: Mapping[str, str],
) -> str | None:
    """Return the declared source or the organization's usual source for a module."""
    if declaration.override is DependencyOverride.GIT:
        return (
            parse_github_repository(declaration.remote) if declaration.remote else None
        )
    if declaration.registry_override is not None or declaration.override in (
        DependencyOverride.ARCHIVE,
        DependencyOverride.LOCAL_PATH,
    ):
        return None
    return module_repositories.get(declaration.module)


def parse_github_repository(remote: str) -> str | None:
    """Return ``owner/name`` for a GitHub HTTPS or SSH remote."""
    if remote.startswith("git@github.com:"):
        remote = f"ssh://git@github.com/{remote.removeprefix('git@github.com:')}"
    try:
        parsed = urlsplit(remote)
    except ValueError:
        return None
    if parsed.hostname != "github.com":
        return None
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2:
        return None
    owner, name = parts[0], parts[1].removesuffix(".git")
    if (
        re.fullmatch(r"[A-Za-z0-9-]+", owner)
        and re.fullmatch(r"[A-Za-z0-9_.-]+", name)
        and name not in {".", ".."}
    ):
        return f"{owner}/{name}"
    return None


def short_revision(revision: str) -> str:
    """Abbreviate full commit hashes; keep tags and branch names readable."""
    return revision[:7] if re.fullmatch(r"[0-9a-f]{40}", revision) else revision


def lookup_bazel_dependency(
    bazel_deps: tuple[DependencyDeclaration, ...],
    dep_name: str,
) -> DependencyDeclaration | None:
    return next((dep for dep in bazel_deps if dep.module == dep_name), None)


def is_tracked_dep_repo(
    entry: RepoEntry,
    tracked_deps: tuple[TrackedDep, ...],
) -> bool:
    return any(
        lookup_bazel_dependency(entry.content.bazel_deps, dep.module_name) is not None
        or entry.matches_repository(dep.repo)
        for dep in tracked_deps
    )
