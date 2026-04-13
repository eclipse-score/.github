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

.ownership-cell {
  font-size: 0.72rem;
  color: var(--muted);
  max-width: 280px;
  line-height: 1.5;
}
.ownership-label { color: var(--muted); font-weight: 500; }

footer {
  max-width: 1400px;
  margin: 2.5rem auto 0;
  font-size: 0.75rem;
  color: var(--muted);
  border-top: 1px solid var(--border);
  padding-top: 1rem;
}
"""

BAZEL_ICON = (
    '<img src="https://bazel.build/_pwa/bazel/icons/icon-72x72.png"'
    ' alt="Bazel" class="icon-bazel">'
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
        '  <button class="tab-btn" data-tab="automation">Delivery &amp; Automation</button>\n'
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
            f'      <th data-sort="ownership">Ownership <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="merged" class="text-right">Merged PRs (30d) <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="issues" class="text-right">Open Issues / PRs <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="release">Latest Release <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="stars" class="text-right">Stars / Forks <span class="sort-arrow"></span></th>\n'
            f"    </tr></thead>\n"
            f"    <tbody>\n{rows}\n    </tbody>\n"
            f"  </table>\n"
            f"</div>\n"
        )
    return "".join(parts)


def _overview_row(entry: RepoEntry, org_name: str) -> str:
    url = f"https://github.com/{org_name}/{entry.name}"
    name_cell = f'<a href="{_e(url)}">{_e(entry.name)}</a>'
    if entry.content.is_bazel_repo:
        name_cell += f" {BAZEL_ICON}"

    ownership = _render_ownership(entry)
    merged = _render_merged_badge(entry.volatile.merged_prs_30_days)
    issues_prs = _render_issues_prs(
        entry.volatile.open_issues,
        entry.volatile.open_ready_prs,
        entry.volatile.open_draft_prs,
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
        f'      <td class="ownership-cell">{ownership}</td>\n'
        f'      <td class="text-right">{merged}</td>\n'
        f'      <td class="text-right">{issues_prs}</td>\n'
        f"      <td>{release}</td>\n"
        f'      <td class="text-right">{stars_forks}</td>\n'
        f"    </tr>"
    )


def _render_ownership(entry: RepoEntry) -> str:
    parts: list[str] = []
    if entry.content.codeowners:
        handles = ", ".join(_e(h) for h in entry.content.codeowners)
        parts.append(f'<span class="ownership-label">Codeowners:</span> {handles}')
    if entry.content.is_bazel_repo and entry.registry.maintainers_in_bazel_registry:
        handles = ", ".join(
            _e(h) for h in entry.registry.maintainers_in_bazel_registry
        )
        parts.append(
            f'<span class="ownership-label">Registry maintainers:</span> {handles}'
        )
    return "<br>".join(parts) if parts else '<span class="text-muted">—</span>'


def _render_merged_badge(count: int) -> str:
    if count >= 10:
        return f'<span class="badge fire">\U0001f525 {count}</span>'
    return str(count)


def _render_issues_prs(issues: int, ready_prs: int, draft_prs: int) -> str:
    prs_part = f"{ready_prs}+{draft_prs}"
    if ready_prs > 5:
        prs_part = f'<span class="badge red">{ready_prs}</span>+{draft_prs}'
    return f"{issues} / {prs_part}"


def _render_release(version: str | None, commits_since: int | None) -> str:
    if version is None and commits_since is None:
        return '<span class="text-muted">—</span>'
    ver = _e(version) if version else "—"
    if commits_since is None:
        return f'<span class="mono">{ver}</span>'
    badge_class = "green" if commits_since == 0 else ("yellow" if commits_since <= 20 else "red")
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
            f'      <th data-sort="bazel">{BAZEL_ICON} Bazel Version <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="dac">Docs-As-Code Version <span class="sort-arrow"></span></th>\n'
            f'      <th data-sort="refint" class="text-center">Reference Integration <span class="sort-arrow"></span></th>\n'
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
    url = f"https://github.com/{org_name}/{entry.name}"
    name_cell = f'<a href="{_e(url)}">{_e(entry.name)}</a>'

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
            f'      <th class="text-center">Gitlint</th>\n'
            f'      <th class="text-center">Pyproject</th>\n'
            f'      <th class="text-center">Pre-commit</th>\n'
            f'      <th class="text-center">GitHub Actions</th>\n'
            f'      <th class="text-center">Daily Workflow</th>\n'
            f'      <th class="text-center">Coverage</th>\n'
            f"    </tr></thead>\n"
            f"    <tbody>\n{rows}\n    </tbody>\n"
            f"  </table>\n"
            f"</div>\n"
        )
    return "".join(parts)


def _automation_row(entry: RepoEntry, org_name: str) -> str:
    url = f"https://github.com/{org_name}/{entry.name}"
    name_cell = f'<a href="{_e(url)}">{_e(entry.name)}</a>'
    if entry.content.is_bazel_repo:
        name_cell += f" {BAZEL_ICON}"

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
        data.append({
            "name": r.name,
            "category": r.category,
            "stars": r.stars,
            "merged": r.volatile.merged_prs_30_days,
            "issues": r.volatile.open_issues,
        })
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
