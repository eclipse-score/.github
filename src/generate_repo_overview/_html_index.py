from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from ._html_common import (
    BAZEL_ICON,
    CSS,
    e,
    language_badge,
    repo_name_cell,
    version_badge,
)
from .metrics_report import (
    get_latest_docs_as_code_release,
    get_max_bazel_version,
    group_repos_by_category,
    has_latest_release,
    parse_version_key,
)

if TYPE_CHECKING:
    from .models import RepoEntry, RepoSnapshot

_INDEX_JS = (Path(__file__).parent / "templates" / "index.js").read_text(
    encoding="utf-8"
)


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
        + _render_timeline_section(repos, snapshot.org_name)
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

    lang_chips = _render_language_distribution(repos)

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
        + (f'  <div id="lang-summary">{lang_chips}</div>\n' if lang_chips else "")
        + "</header>\n\n"
    )


def _render_language_distribution(repos: list[RepoEntry]) -> str:
    counts = Counter(
        r.content.top_languages[0] for r in repos if r.content.top_languages
    )
    if not counts:
        return ""
    top = counts.most_common(4)
    other = sum(counts.values()) - sum(c for _, c in top)
    parts = [
        f"{language_badge(lang)} <span class='lang-count'>{count}</span>"
        for lang, count in top
    ]
    if other > 0:
        parts.append(f'<span class="text-muted">+{other} other</span>')
    return " ".join(parts)


def _render_tab_bar() -> str:
    return (
        '<div class="tab-bar">\n'
        '  <button class="tab-btn active" data-tab="overview">Repository Overview</button>\n'
        '  <button class="tab-btn" data-tab="versions">Versions</button>\n'
        '  <button class="tab-btn" data-tab="tech-stack">Tech Stack</button>\n'
        '  <button class="tab-btn" data-tab="timeline">Releases</button>\n'
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
            f'      <th data-sort="merged" class="text-right" title="Number of pull requests merged into the main branch in the last 30 days. A higher number means more active development.">Merged PRs (30d) <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="issues" class="text-right" data-tooltip="Number of open issues in this repository, including bug reports and feature requests.">Open Issues <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="prs" class="text-right" data-tooltip="Open pull requests: the first number is ready for review, the second is still in draft. A red badge means more than 5 are waiting for review.">Open PRs <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="release" title="The most recent published release. Green = no unreleased commits, yellow = up to 20 commits not yet released, red = more than 20 commits not yet released.">Latest Release <span class="sort-arrow"></span></th>\n'
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

    cnt = entry.volatile.merged_prs_30_days
    if cnt == 0:
        merged_tip = "No pull requests were merged in the last 30 days."
    elif cnt >= 10:
        merged_tip = f"\U0001f525 {cnt} pull requests merged in the last 30 days — very active!"
    else:
        merged_tip = (
            f"{cnt} pull request{'s' if cnt != 1 else ''} merged in the last 30 days."
        )

    n = entry.volatile.open_issues
    issues_tip = f"{n} open issue{'s' if n != 1 else ''} in this repository."

    ready = entry.volatile.open_ready_prs
    draft = entry.volatile.open_draft_prs
    total_prs = ready + draft
    prs_tip = f"{ready} ready for review + {draft} in draft — {total_prs} open pull request{'s' if total_prs != 1 else ''} in total."

    ver = entry.volatile.latest_release_version
    commits = entry.volatile.commits_since_latest_release
    if ver is None:
        release_tip = "No release has been published for this repository."
    elif commits is None:
        release_tip = str(ver)
    elif commits == 0:
        release_tip = f"{ver} — the main branch is fully up to date with this release."
    else:
        release_tip = f"{ver} — {commits} commit{'s' if commits != 1 else ''} on the main branch not yet included in a release."

    stars_tip = f"{entry.stars} star{'s' if entry.stars != 1 else ''} · {entry.forks} fork{'s' if entry.forks != 1 else ''}"

    return (
        f'    <tr data-name="{e(entry.name)}" data-merged="{entry.volatile.merged_prs_30_days}"'
        f' data-issues="{entry.volatile.open_issues}" data-stars="{entry.stars}">\n'
        f"      <td>{name_cell}</td>\n"
        f'      <td class="text-right" data-tooltip="{e(merged_tip)}">{merged}</td>\n'
        f'      <td class="text-right" data-tooltip="{e(issues_tip)}">{issues_cell}</td>\n'
        f'      <td class="text-right" data-tooltip="{e(prs_tip)}">{prs_cell}</td>\n'
        f'      <td data-tooltip="{e(release_tip)}">{release}</td>\n'
        f'      <td class="text-right" data-tooltip="{e(stars_tip)}">{stars_forks}</td>\n'
        f"    </tr>"
    )


def _render_merged_badge(count: int) -> str:
    if count >= 10:
        return f'<span class="badge fire">\U0001f525 {count}</span>'
    return str(count)


def _render_issues_cell(issues: int, repo_url: str) -> str:
    if issues == 0:
        return '<span class="text-muted">—</span>'
    url = e(f"{repo_url}/issues")
    return (
        f'<a href="{url}" class="gh-count" target="_blank" rel="noopener">{issues}</a>'
    )


def _render_prs_cell(ready_prs: int, draft_prs: int, repo_url: str) -> str:
    if ready_prs == 0 and draft_prs == 0:
        return '<span class="text-muted">—</span>'
    url = e(f"{repo_url}/pulls")
    if ready_prs > 5:
        content = f'<span class="badge red">{ready_prs}</span>+{draft_prs}'
    else:
        content = f"{ready_prs}+{draft_prs}"
    return (
        f'<a href="{url}" class="gh-count" target="_blank" rel="noopener">{content}</a>'
    )


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


_DAC_DEP_NAME = "score_docs_as_code"


def _build_version_tooltip(
    *,
    dependency_version_as_used_on_main_branch: str | None,
    latest_available_dependency_version: str | None,
    dependency_version_as_used_in_last_release: str | None,
    component_name: str,
    last_release_tag: str | None = None,
) -> str:
    """Build a human-readable tooltip for version comparison.

    Generic function to compare a component's current version (on main) with the
    latest available version and what was used in the last release.

    Args:
        dependency_version_as_used_on_main_branch: Version currently in use on main branch
        latest_available_dependency_version: Latest available version globally
        dependency_version_as_used_in_last_release: Version used in the most recent release
        component_name: Human-readable component name (e.g., "Bazel", "Docs-As-Code")
        last_release_tag: Optional release tag for "was X at <tag>" suffix

    Returns:
        Human-readable tooltip text
    """
    if dependency_version_as_used_on_main_branch is not None:
        assert (
            dependency_version_as_used_on_main_branch
            == dependency_version_as_used_on_main_branch.strip()
        )
    if latest_available_dependency_version is not None:
        assert (
            latest_available_dependency_version
            == latest_available_dependency_version.strip()
        )

    # Handle component not in use
    if not dependency_version_as_used_on_main_branch:
        if dependency_version_as_used_in_last_release:
            return (
                f"{component_name} is not currently used on the main branch,"
                f" but was used in the last release."
            )
        else:
            return f"{component_name} is not used in this repository."

    # Handle missing latest version (no comparison possible)
    if latest_available_dependency_version is None:
        return f"{component_name} {dependency_version_as_used_on_main_branch} is in use."

    # Build intro: note if version changed between the last release and main
    version_changed = (
        dependency_version_as_used_in_last_release
        and last_release_tag
        and dependency_version_as_used_in_last_release
        != dependency_version_as_used_on_main_branch
    )
    if version_changed:
        tip = (
            f"{component_name} was {dependency_version_as_used_in_last_release}"
            f" at {last_release_tag}, updated to"
            f" {dependency_version_as_used_on_main_branch} on the main branch"
        )
    else:
        tip = f"{component_name} {dependency_version_as_used_on_main_branch}"

    # Append up-to-date status
    if dependency_version_as_used_on_main_branch == latest_available_dependency_version:
        tip += " — now up to date." if version_changed else " — up to date (latest known version)."
    else:
        current_parts = parse_version_key(dependency_version_as_used_on_main_branch)
        latest_parts = parse_version_key(latest_available_dependency_version)
        is_patch_only = (
            current_parts
            and latest_parts
            and len(current_parts) >= 2
            and len(latest_parts) >= 2
            and current_parts[:2] == latest_parts[:2]
        )
        if is_patch_only:
            tip += f" — a patch update to {latest_available_dependency_version} is available."
        else:
            tip += f" — an update to {latest_available_dependency_version} is available."

    return tip


def _render_dep_changes(
    entry: RepoEntry, excluded_deps: frozenset[str] = frozenset()
) -> tuple[str, str]:
    """Return (cell_html, tooltip) for the Other Dep Changes column."""
    if entry.volatile.latest_release_version is None:
        return '<span class="text-muted">—</span>', "No release has been published — nothing to compare against."

    head_deps = dict(entry.content.bazel_deps)
    release_deps = dict(entry.volatile.release_bazel_deps)

    changes: list[str] = []
    all_names = sorted(set(head_deps) | set(release_deps))
    for name in all_names:
        if name in excluded_deps:
            continue
        hv = head_deps.get(name)
        rv = release_deps.get(name)
        if hv != rv:
            changes.append(f"{name}: {rv or '—'} → {hv or '—'}")

    count = len(changes)
    if count == 0:
        tip = f"No dependency changes between {entry.volatile.latest_release_version} and the current main branch."
        cell = '<span class="badge green">no changes</span>'
        return cell, tip

    badge_class = "yellow" if count <= 5 else "red"
    cell = f'<span class="badge {badge_class}">{count} changed</span>'
    tip = "; ".join(changes[:8])
    if len(changes) > 8:
        tip += f" (+{len(changes) - 8} more)"
    return cell, tip


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
            f'      <th data-sort="bazel" title="The version of Bazel (the build tool) in use. Green = on the latest known version, red = a newer version is available.">{BAZEL_ICON} Bazel Version <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="dac" title="The version of the Docs-As-Code tooling in use. Green = up to date, yellow = a patch update is available, red = a major or minor update is needed.">Docs-As-Code Version <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="refint" class="text-center" title="Whether this repository is included in the shared reference integration test suite.">Reference Integration <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="release" title="The most recent published release. Green = no unreleased commits, yellow = up to 20 commits not yet released, red = more than 20 commits not yet released.">Latest Release <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="depchanges" title="Number of dependency version changes on the main branch since the last release. Bazel and Docs-As-Code versions are shown in their own columns.">Other Dep Changes <span class="sort-arrow"></span></th>\n'
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
    release_bazel = entry.volatile.release_bazel_version
    if release_bazel and release_bazel != entry.content.bazel_version:
        bazel_cell = (
            f'<span class="mono text-muted">{e(release_bazel)}</span> → {bazel_cell}'
        )

    release_deps = dict(entry.volatile.release_bazel_deps)
    release_dac = release_deps.get(_DAC_DEP_NAME)
    dac_cell = version_badge(
        entry.content.docs_as_code_version, None, latest_dac=latest_dac, is_bazel=False
    )
    if release_dac and release_dac != entry.content.docs_as_code_version:
        dac_cell = f'<span class="mono text-muted">{e(release_dac)}</span> → {dac_cell}'

    # Deps rendered in their own column — excluded from "Other Dep Changes"
    dedicated_deps = frozenset({_DAC_DEP_NAME})
    refint = (
        '<span class="badge green">yes</span>'
        if entry.content.referenced_by_reference_integration
        else '<span class="text-muted">no</span>'
    )

    # Format latest Bazel version as string for generic comparison
    max_bazel_str = ".".join(str(x) for x in max_bazel) if max_bazel else None
    bazel_tip = _build_version_tooltip(
        dependency_version_as_used_on_main_branch=entry.content.bazel_version,
        latest_available_dependency_version=max_bazel_str,
        dependency_version_as_used_in_last_release=release_bazel,
        component_name="Bazel",
        last_release_tag=entry.volatile.latest_release_version,
    )

    # Generate Docs-As-Code version comparison tooltip
    dac_tip = _build_version_tooltip(
        dependency_version_as_used_on_main_branch=entry.content.docs_as_code_version,
        latest_available_dependency_version=latest_dac,
        dependency_version_as_used_in_last_release=release_dac,
        component_name="Docs-As-Code",
        last_release_tag=entry.volatile.latest_release_version,
    )

    refint_tip = (
        "This repository is included in the shared reference integration."
        if entry.content.referenced_by_reference_integration
        else "This repository is not included in the shared reference integration."
    )

    release = _render_release(
        entry.volatile.latest_release_version,
        entry.volatile.commits_since_latest_release,
    )
    ver = entry.volatile.latest_release_version
    commits = entry.volatile.commits_since_latest_release
    if ver is None:
        release_tip = "No release has been published for this repository."
    elif commits is None:
        release_tip = str(ver)
    elif commits == 0:
        release_tip = f"{ver} — the main branch is fully up to date with this release."
    else:
        release_tip = f"{ver} — {commits} commit{'s' if commits != 1 else ''} on the main branch not yet included in a release."

    dep_changes_cell, dep_changes_tip = _render_dep_changes(entry, dedicated_deps)

    return (
        f"    <tr>\n"
        f"      <td>{name_cell}</td>\n"
        f'      <td data-tooltip="{e(bazel_tip)}">{bazel_cell}</td>\n'
        f'      <td data-tooltip="{e(dac_tip)}">{dac_cell}</td>\n'
        f'      <td class="text-center" data-tooltip="{e(refint_tip)}">{refint}</td>\n'
        f'      <td data-tooltip="{e(release_tip)}">{release}</td>\n'
        f'      <td data-tooltip="{e(dep_changes_tip)}">{dep_changes_cell}</td>\n'
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
            f'<div class="section hidden" data-tab="tech-stack" data-category="{e(category)}">\n'
            f'  <div class="section-header">\n'
            f'    <span class="section-title">{e(category)}</span>\n'
            f'    <span class="section-count">{len(cat_repos)}</span>\n'
            f"  </div>\n"
            f"  <table>\n"
            f"    <thead><tr>\n"
            f'      <th data-sort="name">Repository <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="lang">Language <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="bazel" class="text-center" title="Whether this repository uses Bazel as its build system.">Bazel <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="gitlint" class="text-center" title="Whether this repository enforces commit message formatting rules (gitlint).">Gitlint <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="pyproject" class="text-center" title="Whether this repository has a pyproject.toml — the standard configuration file for Python projects.">Pyproject <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="precommit" class="text-center" title="Whether this repository runs automated checks (formatting, linting, etc.) before each commit is accepted.">Pre-commit <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="ci" class="text-center" title="Whether this repository has automated CI/CD pipelines that run on every push or pull request.">GitHub Actions <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="daily" class="text-center" title="Whether this repository has a scheduled daily job that runs automated tests and checks.">Daily Workflow <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="coverage" class="text-center" title="Whether this repository measures test coverage — tracking how much of the code is exercised by automated tests.">Coverage <span class="sort-arrow"></span></th>\n'
            f"    </tr></thead>\n"
            f"    <tbody>\n{rows}\n    </tbody>\n"
            f"  </table>\n"
            f"</div>\n"
        )
    return "".join(parts)


def _automation_row(entry: RepoEntry, org_name: str) -> str:
    name_cell = repo_name_cell(entry, org_name, bazel_icon=False)
    c = entry.content

    def _presence(val: bool, icon: str) -> str:
        if val:
            return f'<span class="badge green">{icon}</span>'
        return '<span class="text-muted">—</span>'

    def _yesno(val: bool) -> str:
        if val:
            return '<span class="badge green">yes</span>'
        return '<span class="text-muted">no</span>'

    tips = {
        "bazel": "This repository uses Bazel as its build system."
        if c.is_bazel_repo
        else "This repository does not use Bazel.",
        "gitlint": "This repository enforces commit message formatting rules (gitlint)."
        if c.has_gitlint_config
        else "This repository has no commit message formatting rules configured.",
        "pyproject": "This repository has a pyproject.toml (standard Python project configuration)."
        if c.has_pyproject_toml
        else "This repository does not have a pyproject.toml.",
        "precommit": "This repository runs automated checks (formatting, linting, etc.) before each commit is accepted."
        if c.has_pre_commit_config
        else "This repository has no automated pre-commit checks configured.",
        "ci": "This repository has automated CI/CD pipelines that run on every push or pull request."
        if c.has_ci
        else "This repository has no automated CI/CD pipelines.",
        "daily": "This repository has a scheduled daily job that runs automated tests and checks."
        if c.uses_cicd_daily_workflow
        else "This repository has no scheduled daily automated checks.",
        "coverage": "This repository measures test coverage — tracking how much of the code is exercised by automated tests."
        if c.has_coverage_config
        else "This repository does not measure test coverage.",
    }

    langs = entry.content.top_languages
    lang_cell = (
        " ".join(language_badge(lang) for lang in langs)
        if langs
        else '<span class="text-muted">—</span>'
    )
    lang_tip = ", ".join(langs) if langs else "Language unknown"

    return (
        f"    <tr>\n"
        f"      <td>{name_cell}</td>\n"
        f'      <td data-tooltip="{e(lang_tip)}">{lang_cell}</td>\n'
        f'      <td class="text-center" data-tooltip="{e(tips["bazel"])}">{_presence(c.is_bazel_repo, BAZEL_ICON)}</td>\n'
        f'      <td class="text-center" data-tooltip="{e(tips["gitlint"])}">{_presence(c.has_gitlint_config, "\U0001f50d")}</td>\n'
        f'      <td class="text-center" data-tooltip="{e(tips["pyproject"])}">{_presence(c.has_pyproject_toml, "\U0001f40d")}</td>\n'
        f'      <td class="text-center" data-tooltip="{e(tips["precommit"])}">{_presence(c.has_pre_commit_config, "\U0001fa9d")}</td>\n'
        f'      <td class="text-center" data-tooltip="{e(tips["ci"])}">{_presence(c.has_ci, "⚙️")}</td>\n'
        f'      <td class="text-center" data-tooltip="{e(tips["daily"])}">{_yesno(c.uses_cicd_daily_workflow)}</td>\n'
        f'      <td class="text-center" data-tooltip="{e(tips["coverage"])}">{_yesno(c.has_coverage_config)}</td>\n'
        f"    </tr>"
    )


_TIMELINE_TIERS: list[tuple[str, int, int | None]] = [
    ("Released in the last 30 days", 0, 30),
    ("Released this quarter (30-90 days ago)", 30, 90),
    ("Released more than 90 days ago", 90, None),
]


def _parse_release_date(r: RepoEntry) -> date | None:
    raw = r.volatile.latest_release_date
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _build_timeline_tier_html(
    with_release: list[tuple[RepoEntry, date]],
    org_name: str,
    today: date,
) -> str:
    html_parts: list[str] = []
    remaining = list(with_release)
    for label, min_days, max_days in _TIMELINE_TIERS:
        tier_rows: list[str] = []
        next_remaining: list[tuple[RepoEntry, date]] = []
        for r, d in remaining:
            age = (today - d).days
            in_tier = age >= min_days and (max_days is None or age < max_days)
            if in_tier:
                tier_rows.append(_timeline_row(r, org_name, d))
            else:
                next_remaining.append((r, d))
        remaining = next_remaining
        if tier_rows:
            html_parts.append(
                f'  <tr class="tier-header"><td colspan="4">{e(label)}</td></tr>\n'
                + "".join(tier_rows)
            )
    return "".join(html_parts)


def _render_timeline_section(repos: list[RepoEntry], org_name: str) -> str:
    today = date.today()

    with_release = sorted(
        ((r, d) for r in repos if (d := _parse_release_date(r)) is not None),
        key=lambda rd: rd[1],
        reverse=True,
    )
    without_release = [r for r in repos if _parse_release_date(r) is None]

    recent_count = sum(1 for _, d in with_release if (today - d).days <= 30)
    unreleased_count = len(without_release)
    summary = (
        f"{recent_count} release{'s' if recent_count != 1 else ''} in the last 30 days"
    )
    if unreleased_count:
        summary += f" · {unreleased_count} repo{'s' if unreleased_count != 1 else ''} with no release"

    tier_html = _build_timeline_tier_html(with_release, org_name, today)

    if without_release:
        unreleased_rows = "".join(
            _timeline_row_unreleased(r, org_name) for r in without_release
        )
        tier_html += (
            '  <tr class="tier-header"><td colspan="4">No release</td></tr>\n'
            + unreleased_rows
        )

    return (
        '<div class="section hidden" data-tab="timeline">\n'
        '  <div class="section-header">\n'
        '    <span class="section-title">Release Timeline</span>\n'
        f'    <span class="section-subtitle text-muted">{e(summary)}</span>\n'
        "  </div>\n"
        "  <table>\n"
        "    <thead><tr>\n"
        "      <th>Repository</th>\n"
        "      <th>Version</th>\n"
        "      <th>Released</th>\n"
        '      <th title="Number of commits on the main branch not yet included in a release. A higher number means the repository has drifted further from its last published version.">Freshness</th>\n'
        "    </tr></thead>\n"
        f"    <tbody>\n{tier_html}    </tbody>\n"
        "  </table>\n"
        "</div>\n"
    )


def _timeline_row(entry: RepoEntry, org_name: str, release_date: object) -> str:
    name_cell = repo_name_cell(entry, org_name)
    ver = entry.volatile.latest_release_version or "—"
    freshness = _render_release(
        entry.volatile.latest_release_version,
        entry.volatile.commits_since_latest_release,
    )
    date_str = str(release_date)
    return (
        f"    <tr>\n"
        f"      <td>{name_cell}</td>\n"
        f'      <td class="mono">{e(ver)}</td>\n'
        f"      <td>{e(date_str)}</td>\n"
        f"      <td>{freshness}</td>\n"
        f"    </tr>\n"
    )


def _timeline_row_unreleased(entry: RepoEntry, org_name: str) -> str:
    name_cell = repo_name_cell(entry, org_name)
    return (
        f"    <tr>\n"
        f"      <td>{name_cell}</td>\n"
        f'      <td class="text-muted">—</td>\n'
        f'      <td class="text-muted">—</td>\n'
        f'      <td class="text-muted">—</td>\n'
        f"    </tr>\n"
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
                "lang": r.content.top_languages[0] if r.content.top_languages else None,
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
