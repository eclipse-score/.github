from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from ._html_common import BAZEL_ICON, CSS, e, repo_name_cell, version_badge
from .metrics_report import (
    get_latest_docs_as_code_release,
    get_max_bazel_version,
    group_repos_by_category,
    has_latest_release,
)

if TYPE_CHECKING:
    from .models import RepoEntry, RepoSnapshot

_INDEX_JS = (Path(__file__).parent / "templates" / "index.js").read_text(encoding="utf-8")


def render_index_page(snapshot: RepoSnapshot) -> str:
    repos = sorted(snapshot.repos, key=lambda r: r.name.casefold())
    categories = group_repos_by_category(repos)
    repos_json = _build_repos_json(repos, snapshot.org_name)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"  <title>Cross-Repo Metrics — {e(snapshot.org_name)}</title>\n"
        f"  <style>{CSS}</style>\n"
        "</head>\n<body>\n"
        + _render_header(snapshot, repos)
        + _render_tab_bar()
        + _render_filters_placeholder()
        + '<div id="sections">\n'
        + _render_overview_sections(categories, snapshot.org_name)
        + _render_versions_sections(categories, repos, snapshot.org_name)
        + _render_automation_sections(categories, snapshot.org_name)
        + "</div>\n"
        + _render_footer(snapshot)
        + _render_script(repos_json, categories)
        + "</body>\n</html>\n"
    )


def _render_header(snapshot: RepoSnapshot, repos: list[RepoEntry]) -> str:
    total = len(repos)
    with_ci = sum(r.content.has_ci for r in repos)
    with_releases = sum(has_latest_release(r) for r in repos)
    with_lint = sum(r.content.has_lint_config for r in repos)
    bazel_repos = sum(r.content.is_bazel_repo for r in repos)

    return (
        "<header>\n"
        "  <h1>Cross-Repo Metrics Report</h1>\n"
        f'  <p class="subtitle">Generated {e(snapshot.generated_at)}</p>\n'
        '  <div id="summary">\n'
        f'    <span class="summary-chip"><span class="dot" style="background:var(--accent)"></span>{total} repositories</span>\n'
        f'    <span class="summary-chip"><span class="dot" style="background:var(--green)"></span>{with_ci} with CI</span>\n'
        f'    <span class="summary-chip"><span class="dot" style="background:var(--yellow)"></span>{with_releases} with releases</span>\n'
        f'    <span class="summary-chip"><span class="dot" style="background:var(--orange)"></span>{bazel_repos} Bazel repos</span>\n'
        f'    <span class="summary-chip"><span class="dot" style="background:var(--muted)"></span>{with_lint} with lint config</span>\n'
        "  </div>\n"
        "</header>\n\n"
    )


def _render_tab_bar() -> str:
    return (
        '<div class="tab-bar">\n'
        '  <button class="tab-btn active" data-tab="overview">Repository Overview</button>\n'
        '  <button class="tab-btn" data-tab="versions">Versions</button>\n'
        '  <button class="tab-btn" data-tab="automation">Tech Stack</button>\n'
        "</div>\n\n"
    )


def _render_filters_placeholder() -> str:
    return '<div id="filters"></div>\n\n'


def _render_overview_sections(
    categories: list[tuple[str, list[RepoEntry]]],
    org_name: str,
) -> str:
    parts: list[str] = []
    for category, cat_repos in categories:
        rows = "\n".join(_overview_row(r, org_name) for r in cat_repos)
        parts.append(
            f'<div class="section" data-tab="overview" data-category="{e(category)}">\n'
            f'  <div class="section-header">\n'
            f'    <span class="section-title">{e(category)}</span>\n'
            f'    <span class="section-count">{len(cat_repos)}</span>\n'
            f"  </div>\n"
            f"  <table>\n"
            f"    <thead><tr>\n"
            f'      <th data-sort="name">Repository <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="merged" class="text-right" title="Pull requests merged in the last 30 days">Merged PRs (30d) <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="issues" class="text-right" data-tooltip="Open issues in this repository">Open Issues <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="prs" class="text-right" data-tooltip="Open pull requests: ready + draft · red badge = more than 5 ready">Open PRs <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="release" title="Latest release tag · badge: green = up to date, yellow = ≤20 commits behind, red = >20 commits behind">Latest Release <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="stars" class="text-right">Stars / Forks <span class="sort-arrow"></span></th>\n'
            f"    </tr></thead>\n"
            f"    <tbody>\n{rows}\n    </tbody>\n"
            f"  </table>\n"
            f"</div>\n"
        )
    return "".join(parts)


def _overview_row(entry: RepoEntry, org_name: str) -> str:
    name_cell = repo_name_cell(entry, org_name)
    repo_url = f"https://github.com/{org_name}/{entry.name}"

    merged = _render_merged_badge(entry.volatile.merged_prs_30_days)
    issues_cell = _render_issues_cell(entry.volatile.open_issues, repo_url)
    prs_cell = _render_prs_cell(
        entry.volatile.open_ready_prs,
        entry.volatile.open_draft_prs,
        repo_url,
    )
    release = _render_release(
        entry.volatile.latest_release_version,
        entry.volatile.commits_since_latest_release,
    )
    stars_forks = f"{entry.stars} / {entry.forks}"

    return (
        f'    <tr data-name="{e(entry.name)}" data-merged="{entry.volatile.merged_prs_30_days}"'
        f' data-issues="{entry.volatile.open_issues}" data-stars="{entry.stars}">\n'
        f"      <td>{name_cell}</td>\n"
        f'      <td class="text-right">{merged}</td>\n'
        f'      <td class="text-right">{issues_cell}</td>\n'
        f'      <td class="text-right">{prs_cell}</td>\n'
        f"      <td>{release}</td>\n"
        f'      <td class="text-right">{stars_forks}</td>\n'
        f"    </tr>"
    )


def _render_merged_badge(count: int) -> str:
    if count >= 10:
        return f'<span class="badge fire">\U0001f525 {count}</span>'
    return str(count)


def _render_issues_cell(issues: int, repo_url: str) -> str:
    url = e(f"{repo_url}/issues")
    return f'<a href="{url}" class="gh-count" target="_blank" rel="noopener">{issues}</a>'


def _render_prs_cell(ready_prs: int, draft_prs: int, repo_url: str) -> str:
    url = e(f"{repo_url}/pulls")
    if ready_prs > 5:
        content = f'<span class="badge red">{ready_prs}</span>+{draft_prs}'
    else:
        content = f"{ready_prs}+{draft_prs}"
    return f'<a href="{url}" class="gh-count" target="_blank" rel="noopener">{content}</a>'


def _render_release(version: str | None, commits_since: int | None) -> str:
    if version is None and commits_since is None:
        return '<span class="text-muted">—</span>'
    ver = e(version) if version else "—"
    if commits_since is None:
        return f'<span class="mono">{ver}</span>'
    badge_class = (
        "green" if commits_since == 0 else ("yellow" if commits_since <= 20 else "red")
    )
    icon = "✓" if commits_since == 0 else str(commits_since)
    return (
        f'<span class="mono">{ver}</span> '
        f'<span class="badge {badge_class}">+{icon}</span>'
    )


def _render_versions_sections(
    categories: list[tuple[str, list[RepoEntry]]],
    repos: list[RepoEntry],
    org_name: str,
) -> str:
    max_bazel = get_max_bazel_version(repos)
    latest_dac = get_latest_docs_as_code_release(repos)
    parts: list[str] = []
    for category, cat_repos in categories:
        rows = "\n".join(
            _versions_row(r, org_name, max_bazel, latest_dac) for r in cat_repos
        )
        parts.append(
            f'<div class="section hidden" data-tab="versions" data-category="{e(category)}">\n'
            f'  <div class="section-header">\n'
            f'    <span class="section-title">{e(category)}</span>\n'
            f'    <span class="section-count">{len(cat_repos)}</span>\n'
            f"  </div>\n"
            f"  <table>\n"
            f"    <thead><tr>\n"
            f'      <th data-sort="name">Repository <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="bazel" title="green = latest known version, red = outdated">{BAZEL_ICON} Bazel Version <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="dac" title="green = latest, yellow = same minor version, red = outdated">Docs-As-Code Version <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="refint" class="text-center" title="Whether this repo is referenced by the shared reference integration">Reference Integration <span class="sort-arrow"></span></th>\n'
            f"    </tr></thead>\n"
            f"    <tbody>\n{rows}\n    </tbody>\n"
            f"  </table>\n"
            f"</div>\n"
        )
    return "".join(parts)


def _versions_row(
    entry: RepoEntry,
    org_name: str,
    max_bazel: tuple[int, ...] | None,
    latest_dac: str | None,
) -> str:
    name_cell = repo_name_cell(entry, org_name)

    bazel_cell = version_badge(
        entry.content.bazel_version, max_bazel, latest_dac=None, is_bazel=True
    )
    dac_cell = version_badge(
        entry.content.docs_as_code_version, None, latest_dac=latest_dac, is_bazel=False
    )
    refint = (
        '<span class="badge green">yes</span>'
        if entry.content.referenced_by_reference_integration
        else '<span class="text-muted">no</span>'
    )

    return (
        f"    <tr>\n"
        f"      <td>{name_cell}</td>\n"
        f"      <td>{bazel_cell}</td>\n"
        f"      <td>{dac_cell}</td>\n"
        f'      <td class="text-center">{refint}</td>\n'
        f"    </tr>"
    )


def _render_automation_sections(
    categories: list[tuple[str, list[RepoEntry]]],
    org_name: str,
) -> str:
    parts: list[str] = []
    for category, cat_repos in categories:
        rows = "\n".join(_automation_row(r, org_name) for r in cat_repos)
        parts.append(
            f'<div class="section hidden" data-tab="automation" data-category="{e(category)}">\n'
            f'  <div class="section-header">\n'
            f'    <span class="section-title">{e(category)}</span>\n'
            f'    <span class="section-count">{len(cat_repos)}</span>\n'
            f"  </div>\n"
            f"  <table>\n"
            f"    <thead><tr>\n"
            f'      <th data-sort="name">Repository <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="bazel" class="text-center" title="Repository uses Bazel as its build system">Bazel <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="gitlint" class="text-center" title="Has a .gitlint configuration file">Gitlint <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="pyproject" class="text-center" title="Has a pyproject.toml (Python project metadata)">Pyproject <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="precommit" class="text-center" title="Has a .pre-commit-config.yaml">Pre-commit <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="ci" class="text-center" title="Has at least one CI workflow under .github/workflows/">GitHub Actions <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="daily" class="text-center" title="Has a scheduled daily CI/CD workflow">Daily Workflow <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="coverage" class="text-center" title="Has a coverage configuration (e.g. .coveragerc)">Coverage <span class="sort-arrow"></span></th>\n'
            f"    </tr></thead>\n"
            f"    <tbody>\n{rows}\n    </tbody>\n"
            f"  </table>\n"
            f"</div>\n"
        )
    return "".join(parts)


def _automation_row(entry: RepoEntry, org_name: str) -> str:
    name_cell = repo_name_cell(entry, org_name)

    def _presence(val: bool, icon: str) -> str:
        if val:
            return f'<span class="badge green">{icon}</span>'
        return '<span class="text-muted">—</span>'

    def _yesno(val: bool) -> str:
        if val:
            return '<span class="badge green">yes</span>'
        return '<span class="text-muted">no</span>'

    return (
        f"    <tr>\n"
        f"      <td>{name_cell}</td>\n"
        f'      <td class="text-center">{_yesno(entry.content.is_bazel_repo)}</td>\n'
        f'      <td class="text-center">{_presence(entry.content.has_gitlint_config, "\U0001f50d")}</td>\n'
        f'      <td class="text-center">{_presence(entry.content.has_pyproject_toml, "\U0001f40d")}</td>\n'
        f'      <td class="text-center">{_presence(entry.content.has_pre_commit_config, "\U0001fa9d")}</td>\n'
        f'      <td class="text-center">{_presence(entry.content.has_ci, "⚙️")}</td>\n'
        f'      <td class="text-center">{_yesno(entry.content.uses_cicd_daily_workflow)}</td>\n'
        f'      <td class="text-center">{_yesno(entry.content.has_coverage_config)}</td>\n'
        f"    </tr>"
    )


def _render_footer(snapshot: RepoSnapshot) -> str:
    return (
        f"\n<footer>\n"
        f"  Cross-repo metrics for <strong>{e(snapshot.org_name)}</strong> "
        f"— generated {e(snapshot.generated_at)}\n"
        f"</footer>\n\n"
    )


def _build_repos_json(repos: list[RepoEntry], org_name: str) -> str:
    data = []
    for r in repos:
        data.append(
            {
                "name": r.name,
                "category": r.category,
                "stars": r.stars,
                "merged": r.volatile.merged_prs_30_days,
                "issues": r.volatile.open_issues,
            }
        )
    return json.dumps(data)


def _render_script(
    repos_json: str,
    categories: list[tuple[str, list[RepoEntry]]],
) -> str:
    cat_names = json.dumps(["all"] + [c for c, _ in categories])
    return (
        f"<script>const categories = {cat_names};</script>\n"
        f"<script>\n{_INDEX_JS}</script>\n"
    )
