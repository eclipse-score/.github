"""Render the policy-sync report as part of the metrics index."""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING

from ._html_common import GITHUB_ICON, e
from .constants import DEFAULT_POLICY_REPORT_FILENAME

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .policy_sync import PolicySyncOutcome, PolicySyncPolicy, PolicySyncReport


def render_policy_sync_section(
    report: PolicySyncReport | None,
    *,
    repository_categories: Mapping[str, str] | None = None,
    raw_json_available: bool = False,
    raw_json_filename: str = DEFAULT_POLICY_REPORT_FILENAME,
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
    policy_definitions = {policy.id: policy for policy in report.policies}
    raw_link = _raw_json_link(raw_json_filename)
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
        + _policy_stat(summary.drifted, "Changes Needed", "changes-required", "X")
        + _policy_stat(summary.not_applicable, "Not Applicable", "not-applicable", "N/A")
        + _optional_policy_stat(summary.evaluation_failures, "Evaluation Errors", "error", "X")
        + _optional_policy_stat(summary.sync_failures, "Sync Failures", "error", "X")
        + _optional_policy_stat(summary.skipped, "Skipped", "not-evaluated", "—")
        + "      </div>\n"
        '    </div>\n'
        '    <div class="policy-sync-stat-group">\n'
        '      <div class="policy-sync-stat-heading">Policy PR states</div>\n'
        '      <div class="policy-sync-stat-list">\n'
        + _policy_pr_stat("open", pull_request_states["open"])
        + _policy_pr_stat("merged", pull_request_states["merged"])
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
            policy_definitions,
        )

    groups = _group_policy_repositories(repositories, repository_categories)
    matrix_sections = "".join(
        _render_policy_matrix_section(
            category,
            category_repositories,
            policies,
            by_pair,
            policy_definitions,
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

    counts = {"open": 0, "merged": 0}
    for outcome in outcomes:
        state = outcome.policy_pr_status
        if state in counts:
            counts[state] += 1
    return counts


def _render_policy_matrix_section(
    category: str | None,
    repositories: list[str],
    policies: list[str],
    by_pair: dict[tuple[str, str], PolicySyncOutcome],
    policy_definitions: Mapping[str, PolicySyncPolicy],
) -> str:
    category_attr = f' data-category="{e(category)}"' if category is not None else ""
    if policies:
        matrix_rows = "\n".join(
            _matrix_row(repository, policies, by_pair) for repository in repositories
        )
        matrix_header = "".join(
            _policy_header(policy, policy_definitions) for policy in policies
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
    policy: str, policy_definitions: Mapping[str, PolicySyncPolicy]
) -> str:
    definition = policy_definitions.get(policy)
    description = definition.description if definition else ""
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


def _optional_policy_stat(
    value: int, label: str, status_class: str, marker: str
) -> str:
    return _policy_stat(value, label, status_class, marker) if value else ""


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
    if (
        status_class == "changes-required"
        and outcome.policy_pr_status == "open"
    ):
        link = _safe_external_url(outcome.pull_request_url or "")
        if link:
            return _policy_pr_badge(outcome.policy_pr_status, href=link)
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
        return "changes-required", "Changes required", "X"
    if outcome.status == "not-applicable":
        return "not-applicable", "Not applicable", "N/A"
    if outcome.status in {"skipped", "sync-error"}:
        return "not-evaluated", "Not evaluated", "—"
    if outcome.status == "error":
        return "error", "Error", "X"
    return "unknown", outcome.status or "Unknown", "?"


def _outcome_tooltip(outcome: PolicySyncOutcome) -> str:
    status_class, label, _ = _status_display(outcome)
    lines = [f"Status: {label}"]
    if status_class != "compliant":
        lines.append(f"Applicable: {outcome.applicable}")
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
        pr_prefix = "Automated policy PR" if status_class == "compliant" else "Pull request"
        lines.append(
            f"{pr_prefix} ({outcome.policy_pr_status or 'unknown'}): "
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
        "download>Download raw JSON</a>"
    )
