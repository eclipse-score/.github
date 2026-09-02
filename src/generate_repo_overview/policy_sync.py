"""Fetch and validate the optional repository policy report."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, cast

from .console import print_status
from .constants import DEFAULT_POLICY_REPORT_FILENAME, DEFAULT_TOKEN_ENV

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from .org_config import PolicyReportConfig

POLICY_REPORT_SCHEMA_VERSION = 2
POLICY_REPORT_FILENAME = DEFAULT_POLICY_REPORT_FILENAME


@dataclass(frozen=True, slots=True)
class PolicySyncSummary:
    """Counters emitted by ``score-repo-policy-sync``."""

    repositories: int = 0
    synchronized: int = 0
    sync_failures: int = 0
    skipped: int = 0
    evaluations: int = 0
    compliant: int = 0
    drifted: int = 0
    not_applicable: int = 0
    evaluation_failures: int = 0
    pull_requests_created: int = 0
    pull_requests_updated: int = 0
    pull_requests_open: int = 0
    pull_requests_recreated: int = 0
    pull_requests_closed: int = 0
    duration_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class PolicySyncChange:
    """One file-level change requested by a policy."""

    path: str
    description: str
    rationale: str | None = None


@dataclass(frozen=True, slots=True)
class PolicySyncPolicy:
    """Policy metadata included in the upstream report."""

    id: str
    title: str = ""
    description: str = ""
    legacy_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PolicySyncOutcome:
    """One repository/policy evaluation from the report."""

    policy_id: str
    repository: str
    applicable: str
    status: str
    changes: tuple[PolicySyncChange, ...] = ()
    pull_request_url: str | None = None
    policy_pr_status: str | None = None
    warnings: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PolicySyncReport:
    """Validated policy-sync report data kept separate from ``RepoSnapshot``."""

    schema_version: int
    summary: PolicySyncSummary
    outcomes: tuple[PolicySyncOutcome, ...]
    policies: tuple[PolicySyncPolicy, ...] = ()


# Short aliases make the public API easier to discover without coupling it to
# the name used by the upstream tool.
PolicyReport = PolicySyncReport
PolicyReportSummary = PolicySyncSummary
PolicyReportOutcome = PolicySyncOutcome
PolicyReportPolicy = PolicySyncPolicy


def parse_policy_sync_report(value: object) -> PolicySyncReport | None:
    """Parse a schema-v2 report, returning ``None`` for unusable input."""

    if not isinstance(value, dict):
        return None
    value = cast("dict[str, Any]", value)
    if value.get("schema_version") != POLICY_REPORT_SCHEMA_VERSION:
        return None
    raw_summary = value.get("summary")
    raw_outcomes = value.get("outcomes")
    raw_policies = value.get("policies", [])
    if (
        not isinstance(raw_summary, dict)
        or not isinstance(raw_outcomes, list)
        or not isinstance(raw_policies, list)
    ):
        return None
    typed_summary = cast("dict[str, Any]", raw_summary)
    typed_outcomes = cast("list[object]", raw_outcomes)
    typed_policies = cast("list[object]", raw_policies)

    summary = _parse_summary(typed_summary)
    if summary is None:
        return None
    policies: list[PolicySyncPolicy] = []
    for raw_policy in typed_policies:
        policy = _parse_policy(raw_policy)
        if policy is None or any(existing.id == policy.id for existing in policies):
            return None
        policies.append(policy)
    outcomes: list[PolicySyncOutcome] = []
    for raw_outcome in typed_outcomes:
        outcome = _parse_outcome(raw_outcome)
        if outcome is None:
            return None
        outcomes.append(outcome)
    return PolicySyncReport(
        schema_version=POLICY_REPORT_SCHEMA_VERSION,
        summary=summary,
        outcomes=tuple(outcomes),
        policies=tuple(policies),
    )


def load_policy_sync_report(path: Path) -> PolicySyncReport | None:
    """Load a local report; missing, malformed, and unsupported files are ignored."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return parse_policy_sync_report(value)


# Compatibility aliases for callers that use the shorter report name.
parse_policy_report = parse_policy_sync_report
load_policy_report = load_policy_sync_report


def policy_sync_report_to_dict(report: PolicySyncReport) -> dict[str, Any]:
    """Return a JSON-compatible representation of a validated report."""

    summary = report.summary
    return {
        "schema_version": report.schema_version,
        "policies": [
            {
                "id": policy.id,
                "title": policy.title,
                "description": policy.description,
                "legacy_names": list(policy.legacy_names),
            }
            for policy in report.policies
        ],
        "summary": {
            "repositories": summary.repositories,
            "synchronized": summary.synchronized,
            "sync_failures": summary.sync_failures,
            "skipped": summary.skipped,
            "evaluations": summary.evaluations,
            "compliant": summary.compliant,
            "drifted": summary.drifted,
            "not_applicable": summary.not_applicable,
            "evaluation_failures": summary.evaluation_failures,
            "pull_requests_created": summary.pull_requests_created,
            "pull_requests_updated": summary.pull_requests_updated,
            "pull_requests_open": summary.pull_requests_open,
            "pull_requests_recreated": summary.pull_requests_recreated,
            "pull_requests_closed": summary.pull_requests_closed,
            "duration_seconds": summary.duration_seconds,
        },
        "outcomes": [
            {
                "policy_id": outcome.policy_id,
                "repository": outcome.repository,
                "applicable": outcome.applicable,
                "status": outcome.status,
                "changes": [
                    {
                        "path": change.path,
                        "description": change.description,
                        "rationale": change.rationale,
                    }
                    for change in outcome.changes
                ],
                "pull_request_url": outcome.pull_request_url,
                "policy_pr_status": outcome.policy_pr_status,
                "warnings": list(outcome.warnings),
                "error": outcome.error,
            }
            for outcome in report.outcomes
        ],
    }


def render_policy_sync_report_json(report: PolicySyncReport) -> str:
    """Serialize a validated report for publication as a download."""

    return (
        json.dumps(policy_sync_report_to_dict(report), indent=2, sort_keys=True) + "\n"
    )


def fetch_policy_report(
    config: PolicyReportConfig,
    *,
    token: str | None = None,
    token_env: str = DEFAULT_TOKEN_ENV,
    gh_runner: Callable[[list[str], str | None], str] | None = None,
    status_prefix: str = "repo-overview",
) -> bool:
    """Fetch the latest completed configured workflow artifact.

    A false return value means that no usable artifact was available.  Fetching
    is deliberately best-effort because it is an enhancement to the Pages
    dashboard and must not prevent the rest of the site from deploying.
    """

    if not config.enabled:
        return False
    resolved_token = token or _resolve_policy_token(token_env)
    runner = gh_runner or _run_gh

    try:
        run_id = _latest_completed_run_id(
            runner(
                [
                    "run",
                    "list",
                    "--repo",
                    config.source_repo,
                    "--workflow",
                    config.workflow,
                    "--status",
                    "completed",
                    "--limit",
                    "1",
                    "--json",
                    "databaseId",
                    "--jq",
                    ".[0].databaseId",
                ],
                resolved_token,
            )
        )
        if run_id is None:
            raise ValueError("no completed workflow run was found")

        with TemporaryDirectory(prefix="policy-sync-report-") as download_dir:
            runner(
                [
                    "run",
                    "download",
                    str(run_id),
                    "--repo",
                    config.source_repo,
                    "--name",
                    config.artifact,
                    "--dir",
                    download_dir,
                ],
                resolved_token,
            )
            matches = sorted(Path(download_dir).rglob(config.filename))
            if not matches:
                raise ValueError(f"{config.filename!r} was not found in the artifact")
            if len(matches) > 1:
                raise ValueError(
                    f"artifact contains multiple {config.filename!r} files"
                )
            report_bytes = matches[0].read_bytes()

        report = _parse_report_bytes(report_bytes)
        if report is None:
            raise ValueError("downloaded policy report is malformed or unsupported")
        config.cache_path.parent.mkdir(parents=True, exist_ok=True)
        config.cache_path.write_bytes(report_bytes)
    except Exception as exc:  # pragma: no cover - individual API failures vary
        print_status(f"Policy sync report unavailable: {exc}", prefix=status_prefix)
        return False

    print_status(
        f"Wrote policy sync report to {config.cache_path}", prefix=status_prefix
    )
    return True


fetch_policy_sync_report = fetch_policy_report


def _resolve_policy_token(token_env: str) -> str | None:
    for name in (token_env, "GITHUB_TOKEN", "GH_TOKEN"):
        value = os.getenv(name)
        if value:
            return value
    return None


def _run_gh(args: list[str], token: str | None) -> str:
    """Run GitHub CLI with the resolved token, returning stdout."""

    environment = os.environ.copy()
    if token:
        # gh accepts both GH_TOKEN and GITHUB_TOKEN.  Setting GH_TOKEN here
        # also makes a custom token environment work consistently.
        environment["GH_TOKEN"] = token
    try:
        result = subprocess.run(
            ["gh", *args],
            check=False,
            capture_output=True,
            cwd=Path.cwd(),
            env=environment,
            text=True,
            timeout=120,
        )
    except OSError as exc:
        raise RuntimeError("GitHub CLI (gh) is not installed") from exc
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(message or "GitHub CLI command failed")
    return result.stdout


def _parse_report_bytes(value: bytes) -> PolicySyncReport | None:
    try:
        return parse_policy_sync_report(json.loads(value))
    except (UnicodeError, json.JSONDecodeError):
        return None


def _latest_completed_run_id(value: str) -> str | None:
    run_id = value.strip()
    return run_id if run_id and run_id != "null" else None


def _parse_summary(value: dict[str, Any]) -> PolicySyncSummary | None:
    integer_fields = (
        "repositories",
        "synchronized",
        "sync_failures",
        "skipped",
        "evaluations",
        "compliant",
        "drifted",
        "not_applicable",
        "evaluation_failures",
        "pull_requests_created",
        "pull_requests_updated",
        "pull_requests_open",
        "pull_requests_recreated",
        "pull_requests_closed",
    )
    parsed: dict[str, int] = {}
    for field_name in integer_fields:
        field_value = value.get(field_name, 0)
        if (
            not isinstance(field_value, int)
            or isinstance(field_value, bool)
            or field_value < 0
        ):
            return None
        parsed[field_name] = field_value
    duration = value.get("duration_seconds", 0.0)
    if (
        not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or duration < 0
    ):
        return None
    return PolicySyncSummary(
        repositories=parsed["repositories"],
        synchronized=parsed["synchronized"],
        sync_failures=parsed["sync_failures"],
        skipped=parsed["skipped"],
        evaluations=parsed["evaluations"],
        compliant=parsed["compliant"],
        drifted=parsed["drifted"],
        not_applicable=parsed["not_applicable"],
        evaluation_failures=parsed["evaluation_failures"],
        pull_requests_created=parsed["pull_requests_created"],
        pull_requests_updated=parsed["pull_requests_updated"],
        pull_requests_open=parsed["pull_requests_open"],
        pull_requests_recreated=parsed["pull_requests_recreated"],
        pull_requests_closed=parsed["pull_requests_closed"],
        duration_seconds=float(duration),
    )


def _parse_policy(value: object) -> PolicySyncPolicy | None:
    if not isinstance(value, dict):
        return None
    typed_value = cast("dict[str, Any]", value)
    policy_id = typed_value.get("id")
    title = typed_value.get("title", "")
    description = typed_value.get("description", "")
    legacy_names = typed_value.get("legacy_names", [])
    if (
        not isinstance(policy_id, str)
        or not policy_id.strip()
        or not isinstance(title, str)
        or not isinstance(description, str)
        or not isinstance(legacy_names, list)
    ):
        return None
    typed_legacy_names_object = cast("list[object]", legacy_names)
    if any(not isinstance(name, str) for name in typed_legacy_names_object):
        return None
    typed_legacy_names = cast("list[str]", legacy_names)
    return PolicySyncPolicy(
        id=policy_id.strip(),
        title=title.strip(),
        description=description.strip(),
        legacy_names=tuple(name.strip() for name in typed_legacy_names if name.strip()),
    )


def _parse_outcome(value: object) -> PolicySyncOutcome | None:  # noqa: C901
    if not isinstance(value, dict):
        return None
    value = cast("dict[str, Any]", value)
    string_fields = ("policy_id", "repository", "applicable", "status")
    if any(not isinstance(value.get(field_name), str) for field_name in string_fields):
        return None
    changes_value = value.get("changes", [])
    warnings_value = value.get("warnings", [])
    if not isinstance(changes_value, list) or not isinstance(warnings_value, list):
        return None
    typed_changes = cast("list[object]", changes_value)
    typed_warnings = cast("list[object]", warnings_value)
    changes: list[PolicySyncChange] = []
    for raw_change in typed_changes:
        if not isinstance(raw_change, dict):
            return None
        typed_change = cast("dict[str, Any]", raw_change)
        path = typed_change.get("path")
        description = typed_change.get("description")
        rationale = typed_change.get("rationale")
        if not isinstance(path, str) or not isinstance(description, str):
            return None
        if rationale is not None and not isinstance(rationale, str):
            return None
        changes.append(PolicySyncChange(path, description, rationale))
    if any(not isinstance(warning, str) for warning in typed_warnings):
        return None

    pull_request_url = value.get("pull_request_url")
    policy_pr_status = value.get("policy_pr_status")
    error = value.get("error")
    if pull_request_url is not None and not isinstance(pull_request_url, str):
        return None
    if policy_pr_status is not None and not isinstance(policy_pr_status, str):
        return None
    if error is not None and not isinstance(error, str):
        return None
    return PolicySyncOutcome(
        policy_id=cast("str", value["policy_id"]),
        repository=cast("str", value["repository"]),
        applicable=cast("str", value["applicable"]),
        status=cast("str", value["status"]),
        changes=tuple(changes),
        pull_request_url=pull_request_url,
        policy_pr_status=policy_pr_status,
        warnings=tuple(cast("str", warning) for warning in typed_warnings),
        error=error,
    )


def render_policy_sync_section(
    report: PolicySyncReport | None,
    *,
    repository_categories: Mapping[str, str] | None = None,
    raw_json_available: bool = False,
    raw_json_filename: str = POLICY_REPORT_FILENAME,
) -> str:
    """Render the policy-sync dashboard section."""

    from ._policy_sync_html import render_policy_sync_section as render

    return render(
        report,
        repository_categories=repository_categories,
        raw_json_available=raw_json_available,
        raw_json_filename=raw_json_filename,
    )
