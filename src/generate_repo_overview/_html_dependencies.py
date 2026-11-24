"""Dependency freshness and reverse-dependency sections of repository detail pages."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from ._html_common import e

if TYPE_CHECKING:
    from .models import (
        DependencyDeclaration,
        DependencyResolution,
        RepoEntry,
        RepoSnapshot,
    )

from .models import DependencyPinKind, short_revision

_MUTED_DASH = '<span class="text-muted">—</span>'


def render_dependencies_section(
    entry: RepoEntry, snapshot: RepoSnapshot, site_root: str
) -> str:
    """Compare default-branch and release dependencies with their sources."""
    head = {d.module: d for d in entry.content.bazel_deps}
    release_tag = entry.volatile.latest_release_version
    release = {d.module: d for d in entry.volatile.release_bazel_deps}
    head_bazel = entry.content.bazel_version
    release_bazel = entry.volatile.release_bazel_version if release_tag else None
    if not (head or release or head_bazel or release_bazel):
        return ""

    rows: list[str] = []
    if head_bazel or release_bazel:
        rows.append(
            _row(
                "<span class='mono'>Bazel</span>",
                _plain(head_bazel),
                _plain(release_bazel) if release_tag else None,
                _change(head_bazel, release_bazel) if release_tag else None,
            )
        )
    for module in sorted(head.keys() | release.keys()):
        head_dep, release_dep = head.get(module), release.get(module)
        name = f"<span class='mono'>{e(module)}</span>"
        head_source = (
            snapshot.dependency_repository(entry, head_dep) if head_dep else None
        )
        release_source = (
            snapshot.dependency_repository(entry, release_dep) if release_dep else None
        )
        head_usage = _usage(head_dep, entry, snapshot)
        release_usage = _usage(release_dep, entry, snapshot) if release_tag else None
        if head_dep and release_dep and head_source != release_source:
            if head_source:
                head_usage += f"<br>{_source_links(head_source, snapshot, site_root)}"
            if release_source and release_usage is not None:
                release_usage += (
                    f"<br>{_source_links(release_source, snapshot, site_root)}"
                )
        elif source := head_source or release_source:
            name += f" {_source_links(source, snapshot, site_root)}"
        rows.append(
            _row(
                name,
                head_usage,
                release_usage,
                _change(
                    head_dep,
                    release_dep,
                )
                if release_tag
                else None,
            )
        )

    release_columns = (
        f"<th>Release ({e(release_tag)})</th><th>Change</th>" if release_tag else ""
    )
    return (
        '<section class="detail-section" id="dependencies">\n'
        '  <div class="section-header"><span class="section-title">Dependencies</span></div>\n'
        '  <div class="detail-body">'
        '<p class="text-muted" style="margin:0 0 0.5rem">'
        "Direct Bazel dependencies as declared in the module files, with root module overrides. "
        "Bazel may select a different version when it resolves the full dependency graph. "
        "Freshness compares the declared pin with the latest release and default branch "
        "for repositories in this overview.</p>"
        "<table><thead><tr><th>Dependency</th><th>Default branch</th>"
        f"{release_columns}</tr></thead>\n"
        f"<tbody>\n{''.join(rows)}</tbody></table></div>\n"
        "</section>\n\n"
    )


def render_used_by_section(
    entry: RepoEntry, snapshot: RepoSnapshot, site_root: str
) -> str:
    """List collected repositories that declare a direct dependency on *entry*.

    Consumers are grouped by organization and category, like the index page,
    so long lists stay readable.
    """
    groups: dict[tuple[int, str], list[str]] = {}
    org_order = {
        org.casefold(): index for index, org in enumerate(snapshot.organization_names)
    }
    consumers = (
        sorted(snapshot.repos, key=lambda r: r.full_name.casefold())
        if snapshot.dependency_sources_available
        else ()
    )
    for consumer in consumers:
        if consumer is entry:
            continue
        head = _used(entry, consumer, consumer.content.bazel_deps, snapshot)
        release = _used(entry, consumer, consumer.volatile.release_bazel_deps, snapshot)
        if not head and not release:
            continue
        release_tag = consumer.volatile.latest_release_version
        release_cell = (
            _consumer_pins(release, consumer, snapshot)
            if release
            else _MUTED_DASH
            if release_tag
            else '<span class="text-muted">no release</span>'
        )
        if release_tag:
            release_cell += f' <span class="text-muted">in {e(release_tag)}</span>'
        owner = consumer.owner or snapshot.org_name
        category = (
            f"{owner} / {consumer.category}"
            if snapshot.additional_org_names
            else consumer.category
        )
        groups.setdefault((org_order.get(owner.casefold(), 0), category), []).append(
            f"<tr><td>{_repository_link(consumer, snapshot, site_root)}</td>"
            f"<td>{_consumer_pins(head, consumer, snapshot) if head else _MUTED_DASH}</td>"
            f"<td>{release_cell}</td></tr>\n"
        )

    rows = [
        f'<tr class="group-header"><td colspan="3">{e(category)} '
        f'<span class="text-muted">({len(group_rows)})</span></td></tr>\n'
        + "".join(group_rows)
        for (_, category), group_rows in sorted(
            groups.items(), key=lambda item: (item[0][0], item[0][1].casefold())
        )
    ]

    body = (
        "<table><thead><tr><th>Repository</th><th>Default branch</th>"
        f"<th>Latest release</th></tr></thead>\n<tbody>\n{''.join(rows)}</tbody></table>"
        if rows
        else '<span class="text-muted">No direct dependency on this repository was found.</span>'
        if snapshot.dependency_sources_available
        else '<span class="text-muted">Consumer data unavailable. Recollect the snapshot to see dependencies.</span>'
    )
    return (
        '<section class="detail-section" id="used-by">\n'
        '  <div class="section-header"><span class="section-title">Used by</span></div>\n'
        '  <div class="detail-body">'
        '<p class="text-muted" style="margin:0 0 0.5rem">'
        "Declared direct dependencies only. Repositories in this overview are searched.</p>"
        f"{body}</div>\n"
        "</section>\n\n"
    )


def _used(
    entry: RepoEntry,
    consumer: RepoEntry,
    declarations: tuple[DependencyDeclaration, ...],
    snapshot: RepoSnapshot,
) -> tuple[DependencyDeclaration, ...]:
    return tuple(
        declaration
        for declaration in declarations
        if (repository := snapshot.dependency_repository(consumer, declaration))
        is not None
        and entry.matches_repository(repository)
    )


def _consumer_pins(
    declarations: tuple[DependencyDeclaration, ...],
    consumer: RepoEntry,
    snapshot: RepoSnapshot,
) -> str:
    if len(declarations) == 1:
        return _usage(declarations[0], consumer, snapshot)
    return "<br>".join(
        f"{e(declaration.module)} {_usage(declaration, consumer, snapshot)}"
        for declaration in declarations
    )


def _row(name: str, head: str, release: str | None, change: str | None) -> str:
    release_cells = (
        f"<td>{release}</td><td>{change}</td>" if release is not None else ""
    )
    return f"<tr><td>{name}</td><td>{head}</td>{release_cells}</tr>\n"


def _plain(version: str | None) -> str:
    return f"<span class='mono'>{e(version)}</span>" if version else _MUTED_DASH


def _change(
    head: str | DependencyDeclaration | None,
    release: str | DependencyDeclaration | None,
) -> str:
    if head == release:
        return _MUTED_DASH
    if release is None:
        return '<span class="badge green">added</span>'
    if head is None:
        return '<span class="badge red">removed</span>'
    return '<span class="badge yellow">changed</span>'


def _source_links(repository: str, snapshot: RepoSnapshot, site_root: str) -> str:
    github = (
        f'<a class="text-muted" href="https://github.com/{e(repository)}" '
        f'target="_blank" rel="noopener">{e(repository)} ↗</a>'
    )
    source = _collected(snapshot, repository)
    if source is None:
        return github
    return f'{github} <a href="{e(site_root + source.detail_path(snapshot.org_name))}">details</a>'


def _repository_link(repo: RepoEntry, snapshot: RepoSnapshot, site_root: str) -> str:
    return (
        f'<a href="{e(site_root + repo.detail_path(snapshot.org_name))}">'
        f"{e(repo.full_name)}</a>"
    )


def _collected(snapshot: RepoSnapshot, repository: str) -> RepoEntry | None:
    return next((r for r in snapshot.repos if r.matches_repository(repository)), None)


def _usage(
    declaration: DependencyDeclaration | None,
    consumer: RepoEntry,
    snapshot: RepoSnapshot,
) -> str:
    """Render the declared pin and how fresh it is."""
    if declaration is None:
        return _MUTED_DASH
    version = e(declaration.display_version)
    if declaration.pinned_revision is None:
        kind = declaration.override.value if declaration.override else "unavailable"
        return (
            f"<span class='mono'>{version}</span> "
            f'<span class="badge muted">{e(kind.replace("_", " "))}</span>'
        )
    repository = snapshot.dependency_repository(consumer, declaration)
    if repository is None:
        return (
            f"<span class='mono'>{version}</span> "
            '<span class="badge muted">source unknown</span>'
        )
    resolution = snapshot.dependency_resolution(consumer, declaration)
    if _collected(snapshot, repository) is None:
        return f"<span class='mono'>{version}</span> <span class=\"badge muted\">outside overview</span>"
    if resolution is None:
        return f"<span class='mono'>{version}</span> <span class=\"badge muted\">comparison unavailable</span>"
    release = _release_badge(resolution)
    if resolution.resolved_sha is None:
        return (
            f"<span class='mono'>{version}</span> "
            f'<span class="badge muted">Git revision unresolved</span> {release}'
        )

    if declaration.pin_kind is DependencyPinKind.BRANCH:
        version += f" ({e(short_revision(resolution.resolved_sha))})"
    pin = (
        f'<a class="mono" href="https://github.com/{e(repository)}/commit/'
        f'{e(resolution.resolved_sha)}" target="_blank" rel="noopener" '
        f'title="{e(resolution.resolved_sha)}">{version}</a>'
    )
    branch = _branch_badge(
        repository,
        snapshot,
        resolution.resolved_sha,
        resolution.ahead_of_default_branch_by,
        resolution.behind_default_branch_by,
    )
    return f"{pin} {release} {branch}"


def _release_badge(resolution: DependencyResolution) -> str:
    if resolution.latest_release is None:
        return '<span class="badge muted">release comparison unavailable</span>'
    latest_release = e(resolution.latest_release)
    update_available = resolution.release_update_available
    if update_available is None:
        return (
            f'<span class="badge muted" title="Release comparison unavailable">'
            f"{latest_release} · comparison unavailable</span>"
        )
    if not update_available:
        label = (
            "latest module release"
            if resolution.registry_update_available is not None
            else "includes latest release"
        )
        return f'<span class="badge green">{label} {latest_release}</span>'
    if resolution.registry_update_available:
        return f'<span class="badge yellow">{latest_release} available</span>'
    behind = resolution.behind_latest_release_by
    return (
        f'<span class="badge yellow" title="{behind} commits of {latest_release} '
        f'are missing">{latest_release} available</span>'
    )


def _branch_badge(
    repository: str,
    snapshot: RepoSnapshot,
    sha: str,
    ahead: int | None,
    behind: int | None,
) -> str:
    source = _collected(snapshot, repository)
    if (
        source is None
        or source.default_branch is None
        or ahead is None
        or behind is None
    ):
        return '<span class="badge muted">branch not comparable</span>'
    branch = source.default_branch
    target = source.default_branch_sha or branch
    compare_url = e(
        f"https://github.com/{repository}/compare/{sha}...{quote(target, safe='')}"
    )
    if ahead and behind:
        return (
            f'<a class="badge red" href="{compare_url}" target="_blank" rel="noopener" '
            f'title="{ahead} ahead, {behind} behind">diverged from {e(branch)}</a>'
        )
    if ahead:
        return (
            f'<a class="badge yellow" href="{compare_url}" target="_blank" rel="noopener">'
            f"{ahead} ahead of {e(branch)}</a>"
        )
    if behind == 0:
        return f'<span class="badge green">at {e(branch)}</span>'
    return (
        f'<a class="badge yellow" href="{compare_url}" target="_blank" rel="noopener">'
        f"{behind} behind {e(branch)}</a>"
    )
