from __future__ import annotations

import fnmatch
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from generate_repo_overview.constants import (
    DEFAULT_POLICY_REPORT_CACHE,
    DEFAULT_POLICY_REPORT_FILENAME,
)
from generate_repo_overview.models import GroupingLevel, TrackedDep, WorkflowSignal


@dataclass(frozen=True, slots=True)
class PolicyReportConfig:
    """Settings for the optional policy-sync report integration."""

    source_repo: str = ""
    workflow: str = ""
    artifact: str = ""
    filename: str = DEFAULT_POLICY_REPORT_FILENAME
    cache_path: Path = DEFAULT_POLICY_REPORT_CACHE

    @property
    def enabled(self) -> bool:
        """Whether a source workflow is configured for this organization."""

        return bool(self.source_repo and self.workflow and self.artifact)

    # These aliases keep the field names convenient for callers that describe
    # the value as a JSON/report filename or a local path.
    @property
    def report_filename(self) -> str:
        return self.filename

    @property
    def json_filename(self) -> str:
        return self.filename

    @property
    def local_path(self) -> Path:
        return self.cache_path

    @property
    def report_path(self) -> Path:
        return self.cache_path

    @property
    def source_repository(self) -> str:
        return self.source_repo

    @property
    def workflow_file(self) -> str:
        return self.workflow

    @property
    def artifact_name(self) -> str:
        return self.artifact

PolicySyncReportConfig = PolicyReportConfig
PolicySyncConfig = PolicyReportConfig

@dataclass(frozen=True, slots=True)
class OrgConfig:
    """Organization-specific settings loaded from a TOML config file."""

    org_name: str
    repo_include_patterns: tuple[str, ...] = ()
    tracked_deps: tuple[TrackedDep, ...] = ()
    workflow_signals: tuple[WorkflowSignal, ...] = ()
    reference_integration_repo: str = ""
    registry_repo: str = ""
    platform_repos: tuple[str, ...] = ()
    grouping_levels: tuple[GroupingLevel, ...] = ()
    policy_report: PolicyReportConfig = field(default_factory=PolicyReportConfig)

    def repo_matches_filter(self, repo_name: str) -> bool:
        if not self.repo_include_patterns:
            return True
        return any(
            fnmatch.fnmatch(repo_name, pattern)
            for pattern in self.repo_include_patterns
        )

    @property
    def policy_sync_report(self) -> PolicyReportConfig:
        """Alias for callers that use the upstream tool's terminology."""

        return self.policy_report

    @property
    def policy_report_source_repo(self) -> str:
        return self.policy_report.source_repo

    @property
    def policy_report_workflow(self) -> str:
        return self.policy_report.workflow

    @property
    def policy_report_artifact(self) -> str:
        return self.policy_report.artifact

    @property
    def policy_report_filename(self) -> str:
        return self.policy_report.filename

    @property
    def policy_report_cache_path(self) -> Path:
        return self.policy_report.cache_path


def load_org_config(path: Path) -> OrgConfig:
    """Load and validate an OrgConfig from a TOML file.

    Raises ``ValueError`` for missing/invalid required fields and malformed
    repo paths.  Silently drops tracked_deps and workflow_signals entries
    that have missing or non-string fields.
    """
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    signals = cast("dict[str, Any]", raw.get("signals", {}))

    org_name = raw.get("org_name")
    if not isinstance(org_name, str) or not org_name.strip():
        raise ValueError("org_name is required in the config file.")

    reference_integration_repo = _str_or(signals.get("reference_integration_repo"), "")
    registry_repo = _str_or(signals.get("registry_repo"), "")
    platform_repos = _parse_repo_list(
        signals.get("platform_repos"),
        field_name="platform_repos",
    )
    for field_name, field_value in (
        ("reference_integration_repo", reference_integration_repo),
        ("registry_repo", registry_repo),
    ):
        if field_value and "/" not in field_value:
            raise ValueError(
                f"{field_name} must be in 'org/repo' format, got '{field_value}'."
            )

    raw_grouping = raw.get("grouping", {})
    if not isinstance(raw_grouping, dict):
        raise ValueError("'grouping' must be a table, not a scalar value.")
    grouping_levels = _parse_grouping_levels(raw_grouping.get("levels"))
    policy_report = _parse_policy_report(raw)

    return OrgConfig(
        org_name=org_name.strip(),
        repo_include_patterns=_parse_string_list(raw.get("repo_include_patterns")),
        tracked_deps=_parse_tracked_deps(signals.get("tracked_deps")),
        workflow_signals=_parse_workflow_signals(signals.get("workflow_signals")),
        reference_integration_repo=reference_integration_repo,
        registry_repo=registry_repo,
        platform_repos=platform_repos,
        grouping_levels=grouping_levels,
        policy_report=policy_report,
    )


def _str_or(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _parse_string_list(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"Expected a list of strings, got {type(value).__name__}.")
    return tuple(
        item.strip() for item in value if isinstance(item, str) and item.strip()
    )


def _parse_tracked_deps(value: object) -> tuple[TrackedDep, ...]:
    if not isinstance(value, list):
        return ()
    result: list[TrackedDep] = []
    for item in cast("list[Any]", value):
        if not isinstance(item, dict):
            continue
        repo = item.get("repo")
        module_name = item.get("module_name")
        if (
            isinstance(repo, str)
            and repo.strip()
            and "/" in repo
            and isinstance(module_name, str)
            and module_name.strip()
        ):
            result.append(
                TrackedDep(repo=repo.strip(), module_name=module_name.strip())
            )
    return tuple(result)


def _parse_repo_list(value: object, *, field_name: str) -> tuple[str, ...]:
    repos = _parse_string_list(value)
    for repo in repos:
        if "/" not in repo:
            raise ValueError(
                f"{field_name} entries must be in 'org/repo' format, got '{repo}'."
            )
    return tuple(dict.fromkeys(repos))


def _parse_grouping_levels(value: object) -> tuple[GroupingLevel, ...]:
    if not isinstance(value, list):
        return ()
    result: list[GroupingLevel] = []
    for item in cast("list[Any]", value):
        if not isinstance(item, dict):
            continue
        property_ = item.get("property")
        default = item.get("default")
        if (
            isinstance(property_, str)
            and property_.strip()
            and isinstance(default, str)
            and default.strip()
        ):
            result.append(
                GroupingLevel(property=property_.strip(), default=default.strip())
            )
    if len(result) > 2:
        raise ValueError(
            f"grouping.levels supports at most 2 entries, got {len(result)}."
        )
    return tuple(result)


def _parse_workflow_signals(value: object) -> tuple[WorkflowSignal, ...]:
    if not isinstance(value, list):
        return ()
    result: list[WorkflowSignal] = []
    for item in cast("list[Any]", value):
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            continue
        reference = item.get("reference")
        if isinstance(reference, str) and reference.strip():
            result.append(
                WorkflowSignal(label=label.strip(), reference=reference.strip())
            )
    return tuple(result)


def _parse_policy_report(raw: dict[str, Any]) -> PolicyReportConfig:  # noqa: C901
    """Parse the optional policy report table with strict validation."""

    section_names = ("policy_report", "policy-report", "policy_sync_report", "policy-sync-report")
    present_sections = [name for name in section_names if raw.get(name) is not None]
    if len(present_sections) > 1:
        raise ValueError(
            "Use only one policy report table in the config file: "
            + ", ".join(present_sections)
        )
    value = raw.get(present_sections[0]) if present_sections else None
    if value is None:
        return PolicyReportConfig()
    if not isinstance(value, dict):
        raise ValueError("'policy_report' must be a table, not a scalar value.")

    allowed = {
        "source_repo",
        "source_repository",
        "workflow",
        "workflow_file",
        "artifact",
        "artifact_name",
        "filename",
        "report_filename",
        "json_filename",
        "report_file",
        "cache_path",
        "local_path",
        "local_cache_path",
        "report_path",
        "cache_file",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(
            "Unknown policy_report setting(s): " + ", ".join(str(key) for key in unknown)
        )

    source_repo = _policy_report_alias_string(
        value,
        ("source_repo", "source_repository"),
        default="",
        label="source repository",
    )
    workflow = _policy_report_alias_string(
        value,
        ("workflow", "workflow_file"),
        default="",
        label="workflow",
    )
    artifact = _policy_report_alias_string(
        value,
        ("artifact", "artifact_name"),
        default="",
        label="artifact",
    )
    filename = _policy_report_alias_string(
        value,
        ("filename", "report_filename", "json_filename", "report_file"),
        default=DEFAULT_POLICY_REPORT_FILENAME,
        label="JSON filename",
    )
    cache_value = _policy_report_alias_string(
        value,
        ("cache_path", "local_path", "local_cache_path", "report_path", "cache_file"),
        default=str(DEFAULT_POLICY_REPORT_CACHE),
        label="cache path",
    )
    configured_core = any((source_repo, workflow, artifact))
    if configured_core and not all((source_repo, workflow, artifact)):
        raise ValueError(
            "policy_report requires source_repo, workflow, and artifact together."
        )
    if source_repo:
        source_parts = source_repo.split("/")
        if len(source_parts) != 2 or not all(source_parts):
            raise ValueError(
                "policy_report.source_repo must be in 'org/repo' format, "
                f"got '{source_repo}'."
            )
    if workflow and (
        "/" in workflow
        or "\\" in workflow
        or ".." in workflow
        or not workflow.endswith((".yml", ".yaml"))
    ):
        raise ValueError(
            "policy_report.workflow must be a workflow filename ending in .yml or .yaml."
        )
    if artifact and any(character.isspace() for character in artifact):
        raise ValueError("policy_report.artifact must not contain whitespace.")
    if not filename.endswith(".json") or Path(filename).name != filename:
        raise ValueError(
            "policy_report filename must be a JSON filename without directory components."
        )

    cache_path = Path(cache_value)
    if cache_path.is_absolute() or ".." in cache_path.parts or cache_path == Path("."):
        raise ValueError(
            "policy_report cache_path must be a non-empty relative path without '..'."
        )
    return PolicyReportConfig(
        source_repo=source_repo,
        workflow=workflow,
        artifact=artifact,
        filename=filename,
        cache_path=cache_path,
    )


def _policy_report_alias_string(
    table: dict[str, Any], keys: tuple[str, ...], *, default: str, label: str
) -> str:
    present = [key for key in keys if key in table]
    if len(present) > 1:
        raise ValueError(
            f"Specify only one policy_report setting for {label}: "
            + ", ".join(present)
        )
    if not present:
        return default
    key = present[0]
    value = table[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"policy_report.{key} must be a non-empty string.")
    return value.strip()
