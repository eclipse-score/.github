from __future__ import annotations

import fnmatch
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
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
    repository_owner: str = ""

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
    """Settings for collecting the repositories of one organization."""

    org_name: str
    repo_include_patterns: tuple[str, ...] = ()
    tracked_deps: tuple[TrackedDep, ...] = ()
    workflow_signals: tuple[WorkflowSignal, ...] = ()
    reference_integration_repo: str = ""
    registry_repo: str = ""
    grouping_levels: tuple[GroupingLevel, ...] = ()
    # Whether collection may start tools such as Bazel inside repository
    # checkouts. These tools execute code from the repository, for example
    # Bazel module extensions. They inherit the collector's environment, so
    # that code can read the GitHub token and leak it. Enable this only for
    # organizations whose default branches are trusted with that token.
    # Collection currently starts no such tools.
    run_repository_tools: bool = False

    def repo_matches_filter(self, repo_name: str) -> bool:
        if not self.repo_include_patterns:
            return True
        return any(
            fnmatch.fnmatch(repo_name, pattern)
            for pattern in self.repo_include_patterns
        )


@dataclass(frozen=True, slots=True)
class OverviewConfig:
    """All settings loaded from an organization config file."""

    # The first organization is the primary one. Its repositories keep the
    # short detail page paths and short names in the rendered output.
    organizations: tuple[OrgConfig, ...]
    platform_repos: tuple[str, ...] = ()
    policy_report: PolicyReportConfig = field(default_factory=PolicyReportConfig)

    @property
    def primary(self) -> OrgConfig:
        return self.organizations[0]


_ORGANIZATION_SETTINGS = {
    "repo_include_patterns",
    "run_repository_tools",
    "reference_integration_repo",
    "registry_repo",
    "grouping_levels",
    "tracked_deps",
    "workflow_signals",
}


def load_org_config(path: Path) -> OverviewConfig:
    """Load and validate the organization config from a TOML file.

    Raises ``ValueError`` for missing/invalid required fields and malformed
    repo paths.  Silently drops tracked_deps and workflow_signals entries
    that have missing or non-string fields.
    """
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    _reject_unknown_settings(
        raw,
        {"organizations", "signals", *_POLICY_REPORT_SECTIONS},
        where="top-level",
    )
    signals = raw.get("signals", {})
    if not isinstance(signals, dict):
        raise ValueError("'signals' must be a table, not a scalar value.")
    signals = cast("dict[str, Any]", signals)
    _reject_unknown_settings(signals, {"platform_repos"}, where="signals")
    return OverviewConfig(
        organizations=_parse_organizations(raw.get("organizations")),
        platform_repos=_parse_repo_list(
            signals.get("platform_repos"), field_name="platform_repos"
        ),
        policy_report=_parse_policy_report(raw),
    )


def _parse_organizations(value: object) -> tuple[OrgConfig, ...]:
    if value is not None and not isinstance(value, dict):
        raise ValueError("'organizations' must be a table.")
    if not value:
        raise ValueError("Configure at least one [organizations.<name>] table.")

    organizations: list[OrgConfig] = []
    seen: set[str] = set()
    for name, table in cast("dict[str, Any]", value).items():
        if not re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", name):
            raise ValueError(f"Invalid GitHub organization name: {name!r}.")
        if name.casefold() in seen:
            raise ValueError(f"Duplicate GitHub organization: {name!r}.")
        seen.add(name.casefold())
        if not isinstance(table, dict):
            raise ValueError(f"Organization settings for {name!r} must be a table.")
        where = f"organizations.{name}"
        table = cast("dict[str, Any]", table)
        _reject_unknown_settings(table, _ORGANIZATION_SETTINGS, where=where)
        if "run_repository_tools" not in table:
            raise ValueError(
                f"{where}.run_repository_tools is required. Set it to true only "
                "if the organization's default branches are trusted with the "
                "collection token."
            )
        organizations.append(
            OrgConfig(
                org_name=name,
                repo_include_patterns=_parse_string_list(
                    table.get("repo_include_patterns")
                ),
                run_repository_tools=_parse_bool(table, "run_repository_tools"),
                reference_integration_repo=_parse_repo(
                    table, "reference_integration_repo", where=where
                ),
                registry_repo=_parse_repo(table, "registry_repo", where=where),
                grouping_levels=_parse_grouping_levels(table.get("grouping_levels")),
                tracked_deps=_parse_tracked_deps(table.get("tracked_deps")),
                workflow_signals=_parse_workflow_signals(table.get("workflow_signals")),
            )
        )
    return tuple(organizations)


def _reject_unknown_settings(
    table: dict[str, Any], allowed: set[str], *, where: str
) -> None:
    """Fail on a misspelled setting instead of silently using its default."""
    unknown = sorted(str(key) for key in set(table) - allowed)
    if unknown:
        raise ValueError(f"Unknown {where} setting(s): " + ", ".join(unknown))


def _parse_bool(table: dict[str, Any], key: str) -> bool:
    value = table[key]
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be true or false.")
    return value


def _parse_repo(table: dict[str, Any], key: str, *, where: str) -> str:
    value = table.get(key)
    if value is None:
        return ""
    if not isinstance(value, str) or not is_safe_repository_path(value.strip()):
        raise ValueError(f"{where}.{key} must be in 'org/repo' format, got {value!r}.")
    return value.strip()


def is_safe_repository_path(value: str) -> bool:
    """Return whether *value* is a safe two-component repository path."""

    if "\\" in value or PureWindowsPath(value).anchor:
        return False
    parts = value.split("/")
    return len(parts) == 2 and all(part and part not in {".", ".."} for part in parts)


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
        if not is_safe_repository_path(repo):
            raise ValueError(
                f"{field_name} entries must be in 'org/repo' format, got '{repo}'."
            )
    return tuple(dict.fromkeys(repos))


def _parse_grouping_levels(value: object) -> tuple[GroupingLevel, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("grouping_levels must be a list of tables.")
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
            f"grouping_levels supports at most 2 entries, got {len(result)}."
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


_POLICY_REPORT_SECTIONS = (
    "policy_report",
    "policy-report",
    "policy_sync_report",
    "policy-sync-report",
)


def _parse_policy_report(raw: dict[str, Any]) -> PolicyReportConfig:  # noqa: C901
    """Parse the optional policy report table with strict validation."""

    present_sections = [
        name for name in _POLICY_REPORT_SECTIONS if raw.get(name) is not None
    ]
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
        "repository_owner",
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
    _reject_unknown_settings(
        cast("dict[str, Any]", value), allowed, where="policy_report"
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
    repository_owner = _policy_report_alias_string(
        value, ("repository_owner",), default="", label="repository owner"
    )
    if repository_owner and not re.fullmatch(
        r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", repository_owner
    ):
        raise ValueError(
            "policy_report.repository_owner must be a GitHub organization name."
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
        repository_owner=repository_owner,
    )


def _policy_report_alias_string(
    table: dict[str, Any], keys: tuple[str, ...], *, default: str, label: str
) -> str:
    present = [key for key in keys if key in table]
    if len(present) > 1:
        raise ValueError(
            f"Specify only one policy_report setting for {label}: " + ", ".join(present)
        )
    if not present:
        return default
    key = present[0]
    value = table[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"policy_report.{key} must be a non-empty string.")
    return value.strip()
