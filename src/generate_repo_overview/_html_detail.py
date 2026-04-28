from __future__ import annotations

from typing import TYPE_CHECKING

from ._html_common import BAZEL_ICON, CSS, GITHUB_ICON, e, language_badge, version_badge

if TYPE_CHECKING:
    from .models import RepoEntry, RepoSnapshot


def render_detail_page(
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
        f"  <title>{e(entry.name)} — {e(org_name)}</title>\n"
        f"  <style>{CSS}</style>\n"
        "</head>\n<body>\n"
        + _render_hero(entry, org_name)
        + _render_stat_grid(entry)
        + _render_release_section(entry)
        + _render_tooling_section(entry)
        + _render_ownership_section(entry)
        + _render_versions_section(entry, max_bazel, latest_dac)
        + _render_footer(snapshot)
        + "</body>\n</html>\n"
    )


def _render_hero(entry: RepoEntry, org_name: str) -> str:
    github_url = f"https://github.com/{org_name}/{entry.name}"
    name_html = e(entry.name)
    if entry.content.is_bazel_repo:
        name_html += f" {BAZEL_ICON}"

    chips = f'<span class="badge muted">{e(entry.category)}</span>'
    if entry.subcategory and entry.subcategory != entry.category:
        chips += f' <span class="badge muted">{e(entry.subcategory)}</span>'
    for lang in entry.content.top_languages:
        chips += f" {language_badge(lang)}"

    desc = e(entry.description) if entry.description else ""

    return (
        "<header>\n"
        '  <nav class="breadcrumb">\n'
        '    <a href="../">Cross-Repo Metrics</a> &rsaquo; '
        f"{e(entry.name)}\n"
        "  </nav>\n"
        f"  <h1>{name_html}"
        f' <a href="{e(github_url)}" class="gh-link" title="Open on GitHub ↗"'
        f' target="_blank" rel="noopener">{GITHUB_ICON}</a>'
        f"</h1>\n"
        f'  <p class="subtitle">{desc}</p>\n'
        f'  <div class="meta-chips">{chips}</div>\n'
        "</header>\n\n"
    )


def _render_stat_grid(entry: RepoEntry) -> str:
    v = entry.volatile
    last_push = e(v.last_push_date) if v.last_push_date else "—"
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
        f'<div class="stat-value">{e(val)}</div>'
        f'<div class="stat-label">{label}</div>'
        f"</div>"
        for val, label in cards
    )
    return f'<div class="stat-grid">\n{items}\n</div>\n\n'


def _render_release_section(entry: RepoEntry) -> str:
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
            f'<span class="mono">{e(v.latest_release_version)}</span>'
            f"</div>"
        )
    if v.latest_release_date:
        items.append(
            f'<div class="info-item">'
            f'<div class="info-label">Release Date</div>'
            f"{e(v.latest_release_date)}"
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


def _render_tooling_section(entry: RepoEntry) -> str:
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
        f'{"&#10003;" if val else "—"}</span> {e(label)}</div>'
        for val, label in signals
    )
    return (
        '<section class="detail-section">\n'
        '  <div class="section-header"><span class="section-title">Build &amp; Tooling</span></div>\n'
        f'  <div class="detail-body"><div class="signal-grid">\n{items}\n  </div></div>\n'
        "</section>\n\n"
    )


def _render_ownership_section(entry: RepoEntry) -> str:
    parts: list[str] = []
    if entry.content.codeowners:
        handles = ", ".join(e(h) for h in entry.content.codeowners)
        parts.append(
            f'<div class="info-item">'
            f'<div class="info-label">Codeowners</div>{handles}</div>'
        )
    if entry.registry.maintainers_in_bazel_registry:
        handles = ", ".join(
            e(h) for h in entry.registry.maintainers_in_bazel_registry
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


def _render_versions_section(
    entry: RepoEntry,
    max_bazel: tuple[int, ...] | None,
    latest_dac: str | None,
) -> str:
    items: list[str] = []

    bazel_badge = version_badge(
        entry.content.bazel_version, max_bazel, latest_dac=None, is_bazel=True
    )
    items.append(
        f'<div class="info-item">'
        f'<div class="info-label">Bazel Version</div>{bazel_badge}</div>'
    )

    dac_badge = version_badge(
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
            f'<span class="mono">{e(entry.registry.latest_bazel_registry_version)}</span>'
            f"</div>"
        )

    return (
        '<section class="detail-section">\n'
        '  <div class="section-header"><span class="section-title">Versions</span></div>\n'
        f'  <div class="detail-body"><div class="info-grid">{"".join(items)}</div></div>\n'
        "</section>\n\n"
    )


def _render_footer(snapshot: RepoSnapshot) -> str:
    return (
        "\n<footer>\n"
        f'  <a href="../">&larr; Back to overview</a>'
        f" — generated {e(snapshot.generated_at)}\n"
        "</footer>\n\n"
    )
