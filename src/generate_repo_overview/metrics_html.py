from __future__ import annotations

import html
import json
from typing import TYPE_CHECKING

from .metrics_report import (
    get_latest_docs_as_code_release,
    get_max_bazel_version,
    group_repos_by_category,
    has_latest_release,
    parse_version_key,
)

if TYPE_CHECKING:
    from .models import RepoEntry, RepoSnapshot

CSS = """\
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #0d1117;
  --surface:   #161b22;
  --border:    #30363d;
  --text:      #c9d1d9;
  --muted:     #8b949e;
  --accent:    #58a6ff;
  --green:     #3fb950;
  --yellow:    #d29922;
  --orange:    #e3702d;
  --red:       #f85149;
  --radius:    8px;
  --mono:      "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  min-height: 100vh;
  padding: 2rem 1.5rem;
}

header {
  max-width: 1400px;
  margin: 0 auto 2rem;
}
h1 { font-size: 1.6rem; font-weight: 600; color: #e6edf3; }
.subtitle { color: var(--muted); font-size: 0.85rem; margin-top: 0.3rem; }

#summary {
  display: flex;
  gap: 1.2rem;
  flex-wrap: wrap;
  font-size: 0.82rem;
  color: var(--muted);
  margin-top: 1.2rem;
}
.summary-chip {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

#filters {
  max-width: 1400px;
  margin: 0 auto 0.8rem;
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
button {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  cursor: pointer;
  font-size: 0.82rem;
  padding: 0.38rem 0.85rem;
  transition: border-color .15s, color .15s;
  white-space: nowrap;
}
button:hover { border-color: var(--accent); color: var(--accent); }
.filter-btn { font-size: 0.78rem; padding: 0.28rem 0.7rem; }
.filter-btn.active { border-color: var(--accent); color: var(--accent); }

#sections {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.tab-bar {
  max-width: 1400px;
  margin: 0 auto 1.2rem;
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.tab-btn {
  font-size: 0.82rem;
  padding: 0.38rem 0.85rem;
}
.tab-btn.active {
  border-color: var(--accent);
  color: var(--accent);
  background: #58a6ff11;
}

.section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}
.section.hidden { display: none; }
.section-header {
  padding: 0.8rem 1.1rem;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.section-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #e6edf3;
}
.section-count {
  font-size: 0.72rem;
  color: var(--muted);
  background: #21262d;
  border-radius: 20px;
  padding: 0.15rem 0.55rem;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}
th {
  text-align: left;
  padding: 0.55rem 0.8rem;
  color: var(--muted);
  font-weight: 500;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
  cursor: pointer;
  user-select: none;
  position: relative;
}
th:hover { color: var(--accent); }
th .sort-arrow { margin-left: 0.3rem; font-size: 0.65rem; }
td {
  padding: 0.5rem 0.8rem;
  border-bottom: 1px solid #21262d;
  vertical-align: middle;
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: #1c2129; }

a {
  color: var(--accent);
  text-decoration: none;
}
a:hover { text-decoration: underline; }

.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 20px;
  padding: 0.18rem 0.55rem;
  border: 1px solid;
  white-space: nowrap;
}
.badge.green  { color: var(--green);  border-color: #3fb95055; background: #3fb95011; }
.badge.yellow { color: var(--yellow); border-color: #d2992255; background: #d2992211; }
.badge.orange { color: var(--orange); border-color: #e3702d55; background: #e3702d11; }
.badge.red    { color: var(--red);    border-color: #f8514955; background: #f8514911; }
.badge.muted  { color: var(--muted);  border-color: var(--border); }
.badge.fire   { color: var(--orange); border-color: #e3702d55; background: #e3702d11; }

.icon-bazel {
  width: 14px;
  height: 14px;
  vertical-align: text-bottom;
}

.mono { font-family: var(--mono); font-size: 0.78rem; }
.text-muted { color: var(--muted); }
.text-right { text-align: right; }
.text-center { text-align: center; }

.presence { text-align: center; }

footer {
  max-width: 1400px;
  margin: 2.5rem auto 0;
  font-size: 0.75rem;
  color: var(--muted);
  border-top: 1px solid var(--border);
  padding-top: 1rem;
}

.gh-link { color: var(--muted); margin-left: 0.3rem; vertical-align: middle; display: inline-flex; cursor: alias; }
.gh-link:hover { color: var(--accent); text-decoration: none; }
.gh-link svg { width: 13px; height: 13px; }

.breadcrumb { font-size: 0.82rem; color: var(--muted); margin-bottom: 0.8rem; }
.breadcrumb a { color: var(--accent); }

.meta-chips { display: flex; gap: 0.5rem; margin-top: 0.6rem; flex-wrap: wrap; }

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;
  margin: 1.5rem auto;
  max-width: 1400px;
}
.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.1rem;
}
.stat-value { font-size: 1.5rem; font-weight: 600; color: #e6edf3; }
.stat-label { font-size: 0.75rem; color: var(--muted); margin-top: 0.25rem; }

.detail-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  max-width: 1400px;
  margin: 0 auto 1.2rem;
  overflow: hidden;
}
.detail-body { padding: 1rem 1.1rem; }

.signal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.5rem 1.5rem;
}
.signal-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  padding: 0.3rem 0;
}
.signal-yes { color: var(--green); }
.signal-no { color: var(--muted); }

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.6rem 2rem;
}
.info-item { font-size: 0.85rem; }
.info-label { color: var(--muted); font-size: 0.75rem; margin-bottom: 0.15rem; }

.gh-count { text-decoration: none; }
.gh-count:hover { text-decoration: none; opacity: 0.8; }

th[data-tooltip] { cursor: help; }
th[data-tooltip]::after {
  content: attr(data-tooltip);
  position: absolute;
  top: calc(100% + 4px);
  left: 50%;
  transform: translateX(-50%);
  background: #1c2129;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 0.72rem;
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  padding: 0.45rem 0.7rem;
  white-space: nowrap;
  z-index: 100;
  pointer-events: none;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
  opacity: 0;
  transition: opacity .15s;
}
th[data-tooltip]:hover::after { opacity: 1; }
"""

BAZEL_ICON = (
    '<img src="https://bazel.build/_pwa/bazel/icons/icon-72x72.png"'
    ' alt="Bazel" class="icon-bazel">'
)

GITHUB_ICON = (
    '<svg viewBox="0 0 16 16" fill="currentColor">'
    '<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17'
    ".55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94"
    "-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87"
    " 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59"
    ".82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27"
    ".68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51"
    '.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07'
    '-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z"/>'
    "</svg>"
)


def render_metrics_html(snapshot: RepoSnapshot) -> str:
    repos = sorted(snapshot.repos, key=lambda r: r.name.casefold())
    categories = group_repos_by_category(repos)
    repos_json = _build_repos_json(repos, snapshot.org_name)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"  <title>Cross-Repo Metrics — {_e(snapshot.org_name)}</title>\n"
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


def _e(text: str) -> str:
    return html.escape(text, quote=True)


def _render_header(snapshot: RepoSnapshot, repos: list[RepoEntry]) -> str:
    total = len(repos)
    with_ci = sum(r.content.has_ci for r in repos)
    with_releases = sum(has_latest_release(r) for r in repos)
    with_lint = sum(r.content.has_lint_config for r in repos)
    bazel_repos = sum(r.content.is_bazel_repo for r in repos)

    return (
        "<header>\n"
        "  <h1>Cross-Repo Metrics Report</h1>\n"
        f'  <p class="subtitle">Generated {_e(snapshot.generated_at)}</p>\n'
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
            f'<div class="section" data-tab="overview" data-category="{_e(category)}">\n'
            f'  <div class="section-header">\n'
            f'    <span class="section-title">{_e(category)}</span>\n'
            f'    <span class="section-count">{len(cat_repos)}</span>\n'
            f"  </div>\n"
            f"  <table>\n"
            f"    <thead><tr>\n"
            f'      <th data-sort="name">Repository <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="merged" class="text-right" title="Pull requests merged in the last 30 days">Merged PRs (30d) <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="issues" class="text-right" data-tooltip="Open issues in this repository">Open Issues <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="prs" class="text-right" data-tooltip="Open pull requests: ready + draft · red badge = more than 5 ready">Open PRs <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="release" title="Latest release tag · badge: green = up to date, yellow = ≤20 commits behind, red = >20 commits behind">Latest Release <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="stars" class="text-right">Stars / Forks <span class="sort-arrow"></span></th>\n'
            f"    </tr></thead>\n"
            f"    <tbody>\n{rows}\n    </tbody>\n"
            f"  </table>\n"
            f"</div>\n"
        )
    return "".join(parts)


def _repo_name_cell(entry: RepoEntry, org_name: str) -> str:
    detail_url = f"{_e(entry.name)}/"
    github_url = f"https://github.com/{org_name}/{entry.name}"
    cell = f'<a href="{detail_url}">{_e(entry.name)}</a>'
    if entry.content.is_bazel_repo:
        cell += f" {BAZEL_ICON}"
    cell += (
        f' <a href="{_e(github_url)}" class="gh-link" title="Open on GitHub ↗"'
        f' target="_blank" rel="noopener">{GITHUB_ICON}</a>'
    )
    return cell


def _overview_row(entry: RepoEntry, org_name: str) -> str:
    name_cell = _repo_name_cell(entry, org_name)
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
        f'    <tr data-name="{_e(entry.name)}" data-merged="{entry.volatile.merged_prs_30_days}"'
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
    url = _e(f"{repo_url}/issues")
    return f'<a href="{url}" class="gh-count" target="_blank" rel="noopener">{issues}</a>'


def _render_prs_cell(ready_prs: int, draft_prs: int, repo_url: str) -> str:
    url = _e(f"{repo_url}/pulls")
    if ready_prs > 5:
        content = f'<span class="badge red">{ready_prs}</span>+{draft_prs}'
    else:
        content = f"{ready_prs}+{draft_prs}"
    return f'<a href="{url}" class="gh-count" target="_blank" rel="noopener">{content}</a>'


def _render_release(version: str | None, commits_since: int | None) -> str:
    if version is None and commits_since is None:
        return '<span class="text-muted">—</span>'
    ver = _e(version) if version else "—"
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
            f'<div class="section hidden" data-tab="versions" data-category="{_e(category)}">\n'
            f'  <div class="section-header">\n'
            f'    <span class="section-title">{_e(category)}</span>\n'
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
    name_cell = _repo_name_cell(entry, org_name)

    bazel_cell = _version_badge(
        entry.content.bazel_version, max_bazel, latest_dac=None, is_bazel=True
    )
    dac_cell = _version_badge(
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


def _version_badge(
    version: str | None,
    max_bazel: tuple[int, ...] | None,
    *,
    latest_dac: str | None,
    is_bazel: bool,
) -> str:
    if version is None or not version.strip():
        return '<span class="badge muted">—</span>'

    cleaned = version.strip()
    parsed = parse_version_key(cleaned)

    if is_bazel:
        if parsed is not None and max_bazel is not None and parsed == max_bazel:
            return f'<span class="badge green">{_e(cleaned)}</span>'
        return f'<span class="badge red">{_e(cleaned)}</span>'

    if latest_dac is None:
        return f'<span class="badge muted">{_e(cleaned)}</span>'
    latest_cleaned = latest_dac.strip()
    if cleaned == latest_cleaned:
        return f'<span class="badge green">{_e(cleaned)}</span>'
    if parsed is not None:
        latest_parsed = parse_version_key(latest_cleaned)
        if (
            latest_parsed is not None
            and len(parsed) >= 2
            and len(latest_parsed) >= 2
            and parsed[:2] == latest_parsed[:2]
        ):
            return f'<span class="badge yellow">{_e(cleaned)}</span>'
    return f'<span class="badge red">{_e(cleaned)}</span>'


def _render_automation_sections(
    categories: list[tuple[str, list[RepoEntry]]],
    org_name: str,
) -> str:
    parts: list[str] = []
    for category, cat_repos in categories:
        rows = "\n".join(_automation_row(r, org_name) for r in cat_repos)
        parts.append(
            f'<div class="section hidden" data-tab="automation" data-category="{_e(category)}">\n'
            f'  <div class="section-header">\n'
            f'    <span class="section-title">{_e(category)}</span>\n'
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
    name_cell = _repo_name_cell(entry, org_name)

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
        f"  Cross-repo metrics for <strong>{_e(snapshot.org_name)}</strong> "
        f"— generated {_e(snapshot.generated_at)}\n"
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
        "<script>\n"
        "  // Tab switching\n"
        "  let activeTab = 'overview';\n"
        "  document.querySelectorAll('.tab-btn').forEach(btn => {\n"
        "    btn.addEventListener('click', () => {\n"
        "      activeTab = btn.dataset.tab;\n"
        "      document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b === btn));\n"
        "      document.querySelectorAll('.section').forEach(s => {\n"
        "        const matchTab = s.dataset.tab === activeTab;\n"
        "        const matchCat = activeCategory === 'all' || s.dataset.category === activeCategory;\n"
        "        s.classList.toggle('hidden', !(matchTab && matchCat));\n"
        "      });\n"
        "    });\n"
        "  });\n"
        "\n"
        "  // Category filtering\n"
        "  let activeCategory = 'all';\n"
        f"  const categories = {cat_names};\n"
        "  const filtersEl = document.getElementById('filters');\n"
        "  function renderFilters() {\n"
        "    filtersEl.innerHTML = categories.map(c =>\n"
        "      `<button class=\"filter-btn ${c === activeCategory ? 'active' : ''}\" data-cat=\"${c}\">`\n"
        "      + `${c === 'all' ? 'All groups' : c}</button>`\n"
        "    ).join('');\n"
        "    filtersEl.querySelectorAll('.filter-btn').forEach(btn => {\n"
        "      btn.addEventListener('click', () => {\n"
        "        activeCategory = btn.dataset.cat;\n"
        "        renderFilters();\n"
        "        document.querySelectorAll('.section').forEach(s => {\n"
        "          const matchTab = s.dataset.tab === activeTab;\n"
        "          const matchCat = activeCategory === 'all' || s.dataset.category === activeCategory;\n"
        "          s.classList.toggle('hidden', !(matchTab && matchCat));\n"
        "        });\n"
        "      });\n"
        "    });\n"
        "  }\n"
        "  renderFilters();\n"
        "\n"
        "  // Column sorting\n"
        "  document.querySelectorAll('th[data-sort]').forEach(th => {\n"
        "    th.addEventListener('click', () => {\n"
        "      const table = th.closest('table');\n"
        "      const tbody = table.querySelector('tbody');\n"
        "      const idx = Array.from(th.parentNode.children).indexOf(th);\n"
        "      const rows = Array.from(tbody.querySelectorAll('tr'));\n"
        "      const asc = th.classList.toggle('sort-asc');\n"
        "      th.parentNode.querySelectorAll('th').forEach(h => { if (h !== th) h.classList.remove('sort-asc'); });\n"
        "      rows.sort((a, b) => {\n"
        "        const av = a.children[idx]?.textContent.trim() || '';\n"
        "        const bv = b.children[idx]?.textContent.trim() || '';\n"
        "        const an = parseFloat(av), bn = parseFloat(bv);\n"
        "        if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;\n"
        "        return asc ? av.localeCompare(bv) : bv.localeCompare(av);\n"
        "      });\n"
        "      rows.forEach(r => tbody.appendChild(r));\n"
        "    });\n"
        "  });\n"
        "</script>\n"
    )


def render_all_pages(snapshot: RepoSnapshot) -> dict[str, str]:
    repos = sorted(snapshot.repos, key=lambda r: r.name.casefold())
    max_bazel = get_max_bazel_version(list(repos))
    latest_dac = get_latest_docs_as_code_release(list(repos))

    pages: dict[str, str] = {
        "index.html": render_metrics_html(snapshot),
    }
    for entry in repos:
        pages[f"{entry.name}/index.html"] = _render_repo_detail_page(
            entry, snapshot.org_name, snapshot, max_bazel, latest_dac
        )
    return pages


def _render_repo_detail_page(
    entry: RepoEntry,
    org_name: str,
    snapshot: RepoSnapshot,
    max_bazel: tuple[int, ...] | None,
    latest_dac: str | None,
) -> str:
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"  <title>{_e(entry.name)} — {_e(org_name)}</title>\n"
        f"  <style>{CSS}</style>\n"
        "</head>\n<body>\n"
        + _render_detail_hero(entry, org_name)
        + _render_detail_stat_grid(entry)
        + _render_detail_release_section(entry)
        + _render_detail_tooling_section(entry)
        + _render_detail_ownership_section(entry)
        + _render_detail_versions_section(entry, max_bazel, latest_dac)
        + _render_detail_footer(snapshot)
        + "</body>\n</html>\n"
    )


def _render_detail_hero(entry: RepoEntry, org_name: str) -> str:
    github_url = f"https://github.com/{org_name}/{entry.name}"
    name_html = _e(entry.name)
    if entry.content.is_bazel_repo:
        name_html += f" {BAZEL_ICON}"

    chips = f'<span class="badge muted">{_e(entry.category)}</span>'
    if entry.subcategory and entry.subcategory != entry.category:
        chips += f' <span class="badge muted">{_e(entry.subcategory)}</span>'

    desc = _e(entry.description) if entry.description else ""

    return (
        "<header>\n"
        '  <nav class="breadcrumb">\n'
        '    <a href="../">Cross-Repo Metrics</a> &rsaquo; '
        f"{_e(entry.name)}\n"
        "  </nav>\n"
        f"  <h1>{name_html}"
        f' <a href="{_e(github_url)}" class="gh-link" title="Open on GitHub ↗"'
        f' target="_blank" rel="noopener">{GITHUB_ICON}</a>'
        f"</h1>\n"
        f'  <p class="subtitle">{desc}</p>\n'
        f'  <div class="meta-chips">{chips}</div>\n'
        "</header>\n\n"
    )


def _render_detail_stat_grid(entry: RepoEntry) -> str:
    v = entry.volatile
    last_push = _e(v.last_push_date) if v.last_push_date else "—"
    prs_text = f"{v.open_ready_prs}+{v.open_draft_prs}"

    cards = [
        (str(entry.stars), "Stars"),
        (str(entry.forks), "Forks"),
        (str(v.open_issues), "Open Issues"),
        (prs_text, "Open PRs (ready+draft)"),
        (str(v.merged_prs_30_days), "Merged PRs (30d)"),
        (last_push, "Last Push"),
    ]

    items = "\n".join(
        f'  <div class="stat-card">'
        f'<div class="stat-value">{_e(val)}</div>'
        f'<div class="stat-label">{label}</div>'
        f"</div>"
        for val, label in cards
    )
    return f'<div class="stat-grid">\n{items}\n</div>\n\n'


def _render_detail_release_section(entry: RepoEntry) -> str:
    v = entry.volatile
    if v.latest_release_version is None and v.latest_release_date is None:
        version_html = '<span class="text-muted">No releases</span>'
        return (
            '<section class="detail-section">\n'
            '  <div class="section-header"><span class="section-title">Release</span></div>\n'
            f'  <div class="detail-body">{version_html}</div>\n'
            "</section>\n\n"
        )

    items: list[str] = []
    if v.latest_release_version:
        items.append(
            f'<div class="info-item">'
            f'<div class="info-label">Latest Version</div>'
            f'<span class="mono">{_e(v.latest_release_version)}</span>'
            f"</div>"
        )
    if v.latest_release_date:
        items.append(
            f'<div class="info-item">'
            f'<div class="info-label">Release Date</div>'
            f"{_e(v.latest_release_date)}"
            f"</div>"
        )
    if v.commits_since_latest_release is not None:
        count = v.commits_since_latest_release
        badge_class = (
            "green" if count == 0 else ("yellow" if count <= 20 else "red")
        )
        items.append(
            f'<div class="info-item">'
            f'<div class="info-label">Commits Since Release</div>'
            f'<span class="badge {badge_class}">{count}</span>'
            f"</div>"
        )

    return (
        '<section class="detail-section">\n'
        '  <div class="section-header"><span class="section-title">Release</span></div>\n'
        f'  <div class="detail-body"><div class="info-grid">{"".join(items)}</div></div>\n'
        "</section>\n\n"
    )


def _render_detail_tooling_section(entry: RepoEntry) -> str:
    c = entry.content
    signals = [
        (c.has_ci, "GitHub Actions (CI)"),
        (c.uses_cicd_daily_workflow, "Daily Workflow"),
        (c.has_lint_config, "Lint Config"),
        (c.has_gitlint_config, "Gitlint"),
        (c.has_pre_commit_config, "Pre-commit"),
        (c.has_pyproject_toml, "pyproject.toml"),
        (c.has_coverage_config, "Coverage Config"),
        (c.is_bazel_repo, "Bazel Repo"),
    ]

    items = "\n".join(
        f'    <div class="signal-item">'
        f'<span class="signal-{"yes" if val else "no"}">'
        f'{"&#10003;" if val else "—"}</span> {_e(label)}</div>'
        for val, label in signals
    )
    return (
        '<section class="detail-section">\n'
        '  <div class="section-header"><span class="section-title">Build &amp; Tooling</span></div>\n'
        f'  <div class="detail-body"><div class="signal-grid">\n{items}\n  </div></div>\n'
        "</section>\n\n"
    )


def _render_detail_ownership_section(entry: RepoEntry) -> str:
    parts: list[str] = []
    if entry.content.codeowners:
        handles = ", ".join(_e(h) for h in entry.content.codeowners)
        parts.append(
            f'<div class="info-item">'
            f'<div class="info-label">Codeowners</div>{handles}</div>'
        )
    if entry.registry.maintainers_in_bazel_registry:
        handles = ", ".join(
            _e(h) for h in entry.registry.maintainers_in_bazel_registry
        )
        parts.append(
            f'<div class="info-item">'
            f'<div class="info-label">Registry Maintainers</div>{handles}</div>'
        )

    if not parts:
        parts.append('<span class="text-muted">No ownership information available</span>')

    return (
        '<section class="detail-section">\n'
        '  <div class="section-header"><span class="section-title">Ownership</span></div>\n'
        f'  <div class="detail-body"><div class="info-grid">{"".join(parts)}</div></div>\n'
        "</section>\n\n"
    )


def _render_detail_versions_section(
    entry: RepoEntry,
    max_bazel: tuple[int, ...] | None,
    latest_dac: str | None,
) -> str:
    items: list[str] = []

    bazel_badge = _version_badge(
        entry.content.bazel_version, max_bazel, latest_dac=None, is_bazel=True
    )
    items.append(
        f'<div class="info-item">'
        f'<div class="info-label">Bazel Version</div>{bazel_badge}</div>'
    )

    dac_badge = _version_badge(
        entry.content.docs_as_code_version, None, latest_dac=latest_dac, is_bazel=False
    )
    items.append(
        f'<div class="info-item">'
        f'<div class="info-label">Docs-As-Code Version</div>{dac_badge}</div>'
    )

    refint = (
        '<span class="badge green">yes</span>'
        if entry.content.referenced_by_reference_integration
        else '<span class="text-muted">no</span>'
    )
    items.append(
        f'<div class="info-item">'
        f'<div class="info-label">Reference Integration</div>{refint}</div>'
    )

    if entry.registry.latest_bazel_registry_version:
        items.append(
            f'<div class="info-item">'
            f'<div class="info-label">Latest Registry Version</div>'
            f'<span class="mono">{_e(entry.registry.latest_bazel_registry_version)}</span>'
            f"</div>"
        )

    return (
        '<section class="detail-section">\n'
        '  <div class="section-header"><span class="section-title">Versions</span></div>\n'
        f'  <div class="detail-body"><div class="info-grid">{"".join(items)}</div></div>\n'
        "</section>\n\n"
    )


def _render_detail_footer(snapshot: RepoSnapshot) -> str:
    return (
        "\n<footer>\n"
        f'  <a href="../">&larr; Back to overview</a>'
        f" — generated {_e(snapshot.generated_at)}\n"
        "</footer>\n\n"
    )
