"""Fetch, validate, and render the optional repository policy report."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ._html_common import GITHUB_ICON, e
from .console import print_status
from .constants import DEFAULT_POLICY_REPORT_FILENAME, DEFAULT_TOKEN_ENV

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from .org_config import PolicyReportConfig

POLICY_REPORT_SCHEMA_VERSION = 2
POLICY_REPORT_FILENAME = DEFAULT_POLICY_REPORT_FILENAME
_GITHUB_API = "https://api.github.com"
_REQUEST_TIMEOUT_SECONDS = 30


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


# Short aliases make the public API easier to discover without coupling it to
# the name used by the upstream tool.
PolicyReport = PolicySyncReport
PolicyReportSummary = PolicySyncSummary
PolicyReportOutcome = PolicySyncOutcome


def parse_policy_sync_report(value: object) -> PolicySyncReport | None:
    """Parse a schema-v2 report, returning ``None`` for unusable input."""

    if not isinstance(value, dict):
        return None
    value = cast("dict[str, Any]", value)
    if value.get("schema_version") != POLICY_REPORT_SCHEMA_VERSION:
        return None
    raw_summary = value.get("summary")
    raw_outcomes = value.get("outcomes")
    if not isinstance(raw_summary, dict) or not isinstance(raw_outcomes, list):
        return None
    typed_summary = cast("dict[str, Any]", raw_summary)
    typed_outcomes = cast("list[object]", raw_outcomes)

    summary = _parse_summary(typed_summary)
    if summary is None:
        return None
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
    )


def load_policy_sync_report(path: Path) -> PolicySyncReport | None:
    """Load a local report; missing, malformed, and unsupported files are ignored."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return parse_policy_sync_report(value)


def load_policy_descriptions(path: Path) -> dict[str, str]:
    """Load cached policy descriptions, returning an empty map when unusable."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(value, dict):
        return {}
    typed_value = cast("dict[object, object]", value)
    return {
        policy_id: description
        for policy_id, description in typed_value.items()
        if isinstance(policy_id, str)
        and policy_id.strip()
        and isinstance(description, str)
        and description.strip()
    }


# Compatibility aliases for callers that use the shorter report name.
parse_policy_report = parse_policy_sync_report
load_policy_report = load_policy_sync_report


def policy_sync_report_to_dict(report: PolicySyncReport) -> dict[str, Any]:
    """Return a JSON-compatible representation of a validated report."""

    summary = report.summary
    return {
        "schema_version": report.schema_version,
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

    return json.dumps(policy_sync_report_to_dict(report), indent=2, sort_keys=True) + "\n"


def fetch_policy_report(
    config: PolicyReportConfig,
    *,
    token: str | None = None,
    token_env: str = DEFAULT_TOKEN_ENV,
    urlopen: Callable[..., Any] | None = None,
    status_prefix: str = "repo-overview",
) -> bool:
    """Fetch the latest completed configured workflow artifact.

    A false return value means that no usable artifact was available.  Fetching
    is deliberately best-effort because it is an enhancement to the Pages
    dashboard and must not prevent the rest of the site from deploying.
    """

    if not config.enabled:
        return False
    # The configured source repository is public, so the GitHub API can be
    # used anonymously.  Prefer a token when one is available because it
    # provides a higher rate limit and is required for private repositories.
    resolved_token = token or _resolve_policy_token(token_env)

    opener = urlopen or urllib.request.urlopen
    try:
        repository = urllib.parse.quote(config.source_repo, safe="/")
        workflow = urllib.parse.quote(config.workflow, safe="")
        runs = _get_json(
            f"{_GITHUB_API}/repos/{repository}/actions/workflows/{workflow}/runs"
            "?status=completed&per_page=20",
            resolved_token,
            opener,
        )
        run_id = _latest_completed_run_id(runs)
        if run_id is None:
            raise ValueError("no completed workflow run was found")

        artifacts = _get_json(
            f"{_GITHUB_API}/repos/{repository}/actions/runs/{run_id}/artifacts"
            "?per_page=100",
            resolved_token,
            opener,
        )
        artifact_id = _find_artifact_id(artifacts, config.artifact)
        if artifact_id is None:
            raise ValueError(f"artifact {config.artifact!r} was not found")

        archive = _get_bytes(
            f"{_GITHUB_API}/repos/{repository}/actions/artifacts/{artifact_id}/zip",
            resolved_token,
            opener,
        )
        report_bytes = _extract_report_bytes(archive, config.filename)
        config.cache_path.parent.mkdir(parents=True, exist_ok=True)
        config.cache_path.write_bytes(report_bytes)
        report = _parse_report_bytes(report_bytes)
        if report is not None:
            descriptions = _fetch_policy_descriptions(
                config,
                report,
                resolved_token,
                opener,
            )
            if descriptions:
                config.descriptions_cache_path.parent.mkdir(
                    parents=True, exist_ok=True
                )
                config.descriptions_cache_path.write_text(
                    json.dumps(descriptions, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
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


def _parse_report_bytes(value: bytes) -> PolicySyncReport | None:
    try:
        return parse_policy_sync_report(json.loads(value))
    except (UnicodeError, json.JSONDecodeError):
        return None


def _fetch_policy_descriptions(
    config: PolicyReportConfig,
    report: PolicySyncReport,
    token: str | None,
    urlopen: Callable[..., Any],
) -> dict[str, str]:
    repository = urllib.parse.quote(config.source_repo, safe="/")
    definitions_path = urllib.parse.quote(config.definitions_path.strip("/"), safe="/")
    descriptions: dict[str, str] = {}
    policy_ids = dict.fromkeys(outcome.policy_id for outcome in report.outcomes)
    for policy_id in policy_ids:
        policy_path = urllib.parse.quote(policy_id, safe="")
        url = (
            f"{_GITHUB_API}/repos/{repository}/contents/"
            f"{definitions_path}/{policy_path}/policy.yml"
        )
        try:
            definition = _get_json(url, token, urlopen)
            content = _decode_policy_definition(definition)
            description = _extract_policy_description(content)
        except Exception:  # pragma: no cover - remote metadata is best effort
            continue
        if description:
            descriptions[policy_id] = description
    return descriptions


def _decode_policy_definition(value: object) -> str:
    if not isinstance(value, dict):
        raise ValueError("policy definition response is not an object")
    typed_value = cast("dict[str, object]", value)
    content = typed_value.get("content")
    encoding = typed_value.get("encoding")
    if not isinstance(content, str) or encoding != "base64":
        raise ValueError("policy definition response has no base64 content")
    try:
        return base64.b64decode(content).decode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise ValueError("policy definition content is not valid UTF-8") from exc


def _extract_policy_description(document: str) -> str | None:
    """Extract only the description field from the small policy YAML files."""

    lines = document.splitlines()
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped.startswith("description:"):
            continue
        prefix_indent = len(line) - len(stripped)
        value = stripped.removeprefix("description:").strip()
        if value and value[0] not in "|>":
            return _strip_yaml_scalar(value)
        if value and value[0] in "|>":
            block = _description_block(lines[index + 1 :], prefix_indent)
            if value[0] == ">":
                return " ".join(line for line in block if line).strip() or None
            return "\n".join(block).strip() or None
        return None
    return None


def _description_block(lines: list[str], parent_indent: int) -> list[str]:
    content: list[str] = []
    content_indent: int | None = None
    for line in lines:
        if not line.strip():
            if content:
                content.append("")
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= parent_indent:
            break
        if content_indent is None:
            content_indent = indent
        content.append(line[content_indent:])
    return content


def _strip_yaml_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'").strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1].strip()
        return decoded if isinstance(decoded, str) else value
    return value.strip()


def _request_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "generate-repo-overview",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get_json(url: str, token: str | None, urlopen: Callable[..., Any]) -> object:
    with urlopen(
        urllib.request.Request(url, headers=_request_headers(token)),
        timeout=_REQUEST_TIMEOUT_SECONDS,
    ) as response:
        return json.loads(response.read())


def _get_bytes(url: str, token: str | None, urlopen: Callable[..., Any]) -> bytes:
    request = urllib.request.Request(url, headers=_request_headers(token))
    if urlopen is not urllib.request.urlopen:
        with urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            payload = response.read()
        return payload if isinstance(payload, bytes) else bytes(payload)

    # The artifact API responds with a redirect to a signed storage URL. Do
    # not forward the GitHub API token to that different host.
    opener = urllib.request.build_opener(_NoRedirectHandler)
    try:
        with opener.open(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code not in (301, 302, 303, 307, 308):
            raise
        redirect_url = exc.headers.get("Location")
        if not redirect_url:
            raise
        redirect_request = urllib.request.Request(
            redirect_url,
            headers={"User-Agent": "generate-repo-overview"},
        )
        with urllib.request.urlopen(
            redirect_request, timeout=_REQUEST_TIMEOUT_SECONDS
        ) as response:
            payload = response.read()
    return payload if isinstance(payload, bytes) else bytes(payload)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Expose the artifact redirect so its API token is not forwarded."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs


def _latest_completed_run_id(value: object) -> int | None:
    if not isinstance(value, dict):
        return None
    value = cast("dict[str, Any]", value)
    if not isinstance(value.get("workflow_runs"), list):
        return None
    candidates: list[dict[str, Any]] = []
    for item in cast("list[object]", value["workflow_runs"]):
        if not isinstance(item, dict):
            continue
        typed_item = cast("dict[str, Any]", item)
        if (
            typed_item.get("status", "completed") == "completed"
            and isinstance(typed_item.get("id"), int)
        ):
            candidates.append(typed_item)
    if not candidates:
        return None
    # GitHub returns runs newest-first, but sorting also makes mocked and cached
    # responses deterministic.
    candidates.sort(
        key=lambda item: (
            str(item.get("created_at", "")),
            _int_or_zero(item.get("run_number")),
            _int_or_zero(item.get("id")),
        ),
        reverse=True,
    )
    return cast("int", candidates[0]["id"])


def _find_artifact_id(value: object, artifact_name: str) -> int | None:
    if not isinstance(value, dict):
        return None
    value = cast("dict[str, Any]", value)
    if not isinstance(value.get("artifacts"), list):
        return None
    for item in cast("list[object]", value["artifacts"]):
        if not isinstance(item, dict):
            continue
        typed_item = cast("dict[str, Any]", item)
        if (
            typed_item.get("name") != artifact_name
            or typed_item.get("expired") is True
        ):
            continue
        if isinstance(typed_item.get("id"), int):
            return cast("int", typed_item["id"])
    return None


def _extract_report_bytes(archive: bytes, filename: str) -> bytes:
    try:
        with zipfile.ZipFile(BytesIO(archive)) as zipped:
            names = zipped.namelist()
            exact = [name for name in names if name == filename]
            matches = exact or [name for name in names if Path(name).name == filename]
            if not matches:
                raise ValueError(f"{filename!r} was not found in the artifact")
            if len(matches) > 1:
                raise ValueError(f"artifact contains multiple {filename!r} files")
            return zipped.read(matches[0])
    except zipfile.BadZipFile:
        # This also makes the fetcher friendly to local test doubles and to a
        # future artifact endpoint that returns the configured file directly.
        if isinstance(json.loads(archive), dict):
            return archive
        raise ValueError("downloaded policy artifact is not a ZIP archive") from None


def _int_or_zero(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


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
        if not isinstance(field_value, int) or isinstance(field_value, bool) or field_value < 0:
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
    policy_descriptions: Mapping[str, str] | None = None,
    repository_categories: Mapping[str, str] | None = None,
    raw_json_available: bool = False,
    raw_json_filename: str = POLICY_REPORT_FILENAME,
) -> str:
    """Render the policy-sync dashboard section for the metrics index."""

    if report is None:
        raw_link = _raw_json_link(raw_json_filename) if raw_json_available else ""
        return (
            '<div class="section hidden" data-tab="policy-sync">\n'
            '  <div class="section-header"><span class="section-title">Policy Sync</span></div>\n'
            '  <div class="policy-sync-unavailable">\n'
            '    <strong>Policy Sync report unavailable.</strong>\n'
            '    <span class="text-muted">The latest completed report could not be fetched or validated.</span>\n'
            f"    {raw_link}\n"
            "  </div>\n"
            "</div>\n"
        )

    policies = list(dict.fromkeys(outcome.policy_id for outcome in report.outcomes))
    repositories = list(dict.fromkeys(outcome.repository for outcome in report.outcomes))
    by_pair = {(outcome.repository, outcome.policy_id): outcome for outcome in report.outcomes}
    raw_link = _raw_json_link(raw_json_filename) if raw_json_available or report is not None else ""
    summary = report.summary
    pull_request_states = _pull_request_state_counts(report.outcomes)
    summary_section = (
        '<div class="section hidden" data-tab="policy-sync">\n'
        '  <div class="section-header">\n'
        '    <span class="section-title">Policy Sync</span>\n'
        "  </div>\n"
        '  <div class="policy-sync-meta">\n'
        '    <span class="section-subtitle">Repository policy compliance</span>\n'
        f"    {raw_link}\n"
        "  </div>\n"
        '  <div class="policy-sync-statistics">\n'
        '    <div class="policy-sync-stat-group">\n'
        '      <div class="policy-sync-stat-heading">Evaluation status</div>\n'
        '      <div class="policy-sync-stat-list">\n'
        + _policy_stat(summary.compliant, "Compliant", "compliant", "✓")
        + _policy_stat(summary.drifted, "Changes Needed", "changes-required", "!")
        + _policy_stat(summary.not_applicable, "Not Applicable", "not-applicable", "N/A")
        + _policy_stat(summary.evaluation_failures, "Evaluation Errors", "error", "!")
        + _policy_stat(summary.sync_failures, "Sync Failures", "error", "!")
        + _policy_stat(summary.skipped, "Skipped", "not-evaluated", "—")
        + "      </div>\n"
        '    </div>\n'
        '    <div class="policy-sync-stat-group">\n'
        '      <div class="policy-sync-stat-heading">Policy PR states</div>\n'
        '      <div class="policy-sync-stat-list">\n'
        + _policy_pr_stat("open", pull_request_states["open"])
        + _policy_pr_stat("merged", pull_request_states["merged"])
        + _policy_pr_stat("closed", pull_request_states["closed"])
        + _policy_pr_stat("none", pull_request_states["none"])
        + "      </div>\n"
        '    </div>\n'
        "  </div>\n"
        "  </div>\n"
    )
    if not policies:
        return summary_section + _render_policy_matrix_section(
            None,
            [],
            [],
            by_pair,
            policy_descriptions,
        )

    groups = _group_policy_repositories(repositories, repository_categories)
    matrix_sections = "".join(
        _render_policy_matrix_section(
            category,
            category_repositories,
            policies,
            by_pair,
            policy_descriptions,
        )
        for category, category_repositories in groups
    )
    return summary_section + matrix_sections


def _group_policy_repositories(
    repositories: list[str],
    repository_categories: Mapping[str, str] | None,
) -> list[tuple[str | None, list[str]]]:
    """Group report repositories in the same order as the dashboard filters."""

    if not repository_categories:
        return [(None, repositories)]

    grouped: dict[str, list[str]] = {}
    ungrouped: list[str] = []
    for repository in repositories:
        category = repository_categories.get(repository)
        if category is None:
            ungrouped.append(repository)
        else:
            grouped.setdefault(category, []).append(repository)

    groups: list[tuple[str | None, list[str]]] = list(grouped.items())
    if ungrouped:
        groups.append((None, ungrouped))
    return groups


def _pull_request_state_counts(
    outcomes: tuple[PolicySyncOutcome, ...],
) -> dict[str, int]:
    """Count the PR states reported for policy evaluations."""

    counts = {
        "open": 0,
        "merged": 0,
        "closed": 0,
        "none": 0,
        "not checked": 0,
        "other": 0,
    }
    for outcome in outcomes:
        state = outcome.policy_pr_status
        if state is None:
            counts["not checked"] += 1
        elif state in {"open", "merged", "closed", "none"}:
            counts[state] += 1
        else:
            counts["other"] += 1
    return counts


def _render_policy_matrix_section(
    category: str | None,
    repositories: list[str],
    policies: list[str],
    by_pair: dict[tuple[str, str], PolicySyncOutcome],
    policy_descriptions: Mapping[str, str] | None,
) -> str:
    category_attr = f' data-category="{e(category)}"' if category is not None else ""
    if policies:
        matrix_rows = "\n".join(
            _matrix_row(repository, policies, by_pair) for repository in repositories
        )
        matrix_header = "".join(
            _policy_header(policy, policy_descriptions) for policy in policies
        )
    else:
        matrix_rows = '<tr><td colspan="2" class="text-muted">No policy evaluations.</td></tr>'
        matrix_header = "<th>Policy</th>"
    title = "Compliance Matrix" if category is None else category
    count = f'<span class="section-count">{len(repositories)}</span>' if category is not None else ""
    return (
        f'<div class="section hidden" data-tab="policy-sync"{category_attr}>\n'
        '  <div class="section-header">\n'
        f'    <span class="section-title">{e(title)}</span>\n'
        f"    {count}\n"
        "  </div>\n"
        '  <div class="policy-sync-matrix">\n'
        '    <table class="policy-matrix">\n'
        "      <thead><tr><th>Repository</th>"
        f"{matrix_header}</tr></thead>\n"
        f"      <tbody>\n{matrix_rows}\n      </tbody>\n"
        "    </table>\n"
        "  </div>\n"
        "</div>\n"
    )


def _policy_header(
    policy: str, policy_descriptions: Mapping[str, str] | None
) -> str:
    description = (policy_descriptions or {}).get(policy)
    if not description:
        return f"<th>{e(policy)}</th>"
    return (
        f'<th data-tooltip="{e(description)}" title="{e(description)}">'
        f"{e(policy)}</th>"
    )


def _policy_stat(value: int, label: str, status_class: str, marker: str) -> str:
    return (
        '        <span class="policy-sync-stat">'
        f'<span class="policy-status {status_class}" aria-label="{e(label)}">'
        f"{e(marker)}</span>"
        f'<span class="policy-sync-stat-value">{value}</span>'
        f'<span class="policy-sync-stat-label">{e(label)}</span>'
        "</span>\n"
    )


def _policy_pr_stat(state: str, value: int) -> str:
    label = _pull_request_state_label(state)
    return (
        '        <span class="policy-sync-stat">'
        f"{_policy_pr_badge(state)}"
        f'<span class="policy-sync-stat-value">{value}</span>'
        f'<span class="policy-sync-stat-label">{e(label)} PRs</span>'
        "</span>\n"
    )


def _matrix_row(
    repository: str,
    policies: list[str],
    by_pair: dict[tuple[str, str], PolicySyncOutcome],
) -> str:
    cells = "".join(
        _matrix_cell_html(by_pair.get((repository, policy)))
        for policy in policies
    )
    return f"        <tr><th>{e(repository)}</th>{cells}</tr>"


def _matrix_cell_html(outcome: PolicySyncOutcome | None) -> str:
    if outcome is None:
        return '<td><span class="policy-status not-applicable" aria-label="Not applicable">N/A</span></td>'
    tooltip = _outcome_tooltip(outcome)
    return (
        f'<td class="policy-matrix-cell" data-tooltip="{e(tooltip)}" '
        f'title="{e(tooltip)}" tabindex="0">{_matrix_cell(outcome)}</td>'
    )


def _matrix_cell(outcome: PolicySyncOutcome | None) -> str:
    if outcome is None:
        return '<span class="policy-status not-applicable" aria-label="Not applicable">N/A</span>'
    status_class, label, marker = _status_display(outcome)
    automated = status_class == "compliant" and bool(outcome.pull_request_url)
    if automated:
        label = "Compliant (automated PR)"
        marker = "✓✓"
    content = (
        f'<span class="policy-status {status_class}" title="{e(label)}" '
        f'aria-label="{e(label)}">{marker}</span>'
    )
    if outcome.pull_request_url and not automated:
        link = _safe_external_url(outcome.pull_request_url)
        if link:
            content += f" {_policy_pr_badge(outcome.policy_pr_status, href=link)}"
    return content


def _pull_request_state_label(state: str | None) -> str:
    return {
        "open": "Open",
        "merged": "Merged",
        "closed": "Closed",
        "none": "No",
    }.get(state or "", state or "PR state not checked")


def _pull_request_state_class(state: str | None) -> str:
    return state if state in {"open", "merged", "closed", "none"} else "unknown"


def _policy_pr_badge(state: str | None, *, href: str | None = None) -> str:
    label = _pull_request_state_label(state)
    state_class = _pull_request_state_class(state)
    badge_content = "—" if state == "none" else f"{GITHUB_ICON}{e(label)}"
    if href is None:
        return (
            f'<span class="policy-pr-badge policy-pr-{state_class}" '
            f'aria-label="{e(label)} PRs">{badge_content}</span>'
        )
    return (
        f'<a href="{href}" class="policy-pr-badge policy-pr-{state_class}" '
        f'aria-label="{e(label)} policy pull request" '
        f'title="View {e(label)} policy pull request" '
        f'target="_blank" rel="noopener">{badge_content}</a>'
    )


def _status_display(outcome: PolicySyncOutcome) -> tuple[str, str, str]:
    if outcome.status in {"compliant", "pull-request-closed"}:
        return "compliant", "Compliant", "✓"
    if outcome.status in {
        "changes-required",
        "pull-request-created",
        "pull-request-updated",
        "pull-request-open",
        "pull-request-recreated",
        "pull-request-recreated-no-changes",
    }:
        return "changes-required", "Changes required", "!"
    if outcome.status == "not-applicable":
        return "not-applicable", "Not applicable", "N/A"
    if outcome.status in {"skipped", "sync-error"}:
        return "not-evaluated", "Not evaluated", "—"
    if outcome.status == "error":
        return "error", "Error", "!"
    return "unknown", outcome.status or "Unknown", "?"


def _outcome_tooltip(outcome: PolicySyncOutcome) -> str:
    _, label, _ = _status_display(outcome)
    lines = [f"Status: {label}", f"Applicable: {outcome.applicable}"]
    if outcome.changes:
        lines.append("Changes:")
        lines.extend(
            f"  {change.path}: {change.description}"
            + (f" ({change.rationale})" if change.rationale else "")
            for change in outcome.changes
        )
    if outcome.warnings:
        lines.append("Warnings:")
        lines.extend(f"  {warning}" for warning in outcome.warnings)
    if outcome.error:
        lines.append(f"Error: {outcome.error}")
    if outcome.pull_request_url:
        lines.append(
            f"Pull request ({outcome.policy_pr_status or 'unknown'}): "
            f"{outcome.pull_request_url}"
        )
    return "\n".join(lines)


def _safe_external_url(value: str) -> str | None:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    if any(character in value for character in "\r\n"):
        return None
    return e(value)


def _raw_json_link(filename: str) -> str:
    return (
        f'<a class="policy-raw-link" href="{e(filename)}" '
        'download>Download raw JSON</a>'
    )
