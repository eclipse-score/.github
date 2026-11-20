"""Dependency freshness and reverse-dependency sections of repository detail pages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._html_common import e

if TYPE_CHECKING:
    from .models import DependencyDeclaration, RepoEntry, RepoSnapshot

_MUTED_DASH = '<span class="text-muted">—</span>'


def render_dependencies_section(
    entry: RepoEntry, snapshot: RepoSnapshot, site_root: str
) -> str:
    """Compare default-branch and release dependencies with their sources."""
    head = {d.module: d for d in entry.content.bazel_deps}
    release_tag = entry.volatile.latest_release_version
    release = {d.module: d for d in entry.volatile.release_bazel_deps}
    if not head and not release and not entry.content.bazel_version:
        return ""

    rows = [
        _row(
            "<span class='mono'>Bazel</span>",
            _plain(entry.content.bazel_version),
            _plain(entry.volatile.release_bazel_version) if release_tag else None,
            _change(entry.content.bazel_version, entry.volatile.release_bazel_version)
            if release_tag
            else None,
        )
    ]
    for module in sorted(head.keys() | release.keys()):
        head_dep, release_dep = head.get(module), release.get(module)
        declaration = head_dep or release_dep
        assert declaration is not None
        rows.append(
            _row(
                _dependency_name(declaration, snapshot, site_root),
                _usage(head_dep, snapshot),
                _usage(release_dep, snapshot) if release_tag else None,
                _change(
                    head_dep.display_version if head_dep else None,
                    release_dep.display_version if release_dep else None,
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
        "Freshness compares each pin with the dependency's latest release and "
        "default branch. It is only known for repositories in this overview.</p>"
        "<table><thead><tr><th>Dependency</th><th>HEAD</th>"
        f"{release_columns}</tr></thead>\n"
        f"<tbody>\n{''.join(rows)}</tbody></table></div>\n"
        "</section>\n\n"
    )


def render_used_by_section(
    entry: RepoEntry, snapshot: RepoSnapshot, site_root: str
) -> str:
    """List collected repositories whose default branch or release uses *entry*."""
    rows: list[str] = []
    for consumer in sorted(snapshot.repos, key=lambda r: r.full_name.casefold()):
        if consumer is entry:
            continue
        head = _used(entry, consumer.content.bazel_deps, snapshot)
        release = _used(entry, consumer.volatile.release_bazel_deps, snapshot)
        if head is None and release is None:
            continue
        release_tag = consumer.volatile.latest_release_version
        release_cell = (
            _usage(release, snapshot)
            if release is not None
            else _MUTED_DASH
            if release_tag
            else '<span class="text-muted">no release</span>'
        )
        if release_tag:
            release_cell += f' <span class="text-muted">in {e(release_tag)}</span>'
        rows.append(
            f"<tr><td>{_repository_link(consumer, snapshot, site_root)}</td>"
            f"<td>{_usage(head, snapshot) if head else _MUTED_DASH}</td>"
            f"<td>{release_cell}</td></tr>\n"
        )

    body = (
        "<table><thead><tr><th>Repository</th><th>Default branch</th>"
        f"<th>Latest release</th></tr></thead>\n<tbody>\n{''.join(rows)}</tbody></table>"
        if rows
        else '<span class="text-muted">No collected repository uses this one.</span>'
    )
    return (
        '<section class="detail-section" id="used-by">\n'
        '  <div class="section-header"><span class="section-title">Used by</span></div>\n'
        '  <div class="detail-body">'
        '<p class="text-muted" style="margin:0 0 0.5rem">'
        "Only repositories in this overview are searched.</p>"
        f"{body}</div>\n"
        "</section>\n\n"
    )


def _used(
    entry: RepoEntry,
    declarations: tuple[DependencyDeclaration, ...],
    snapshot: RepoSnapshot,
) -> DependencyDeclaration | None:
    for declaration in declarations:
        repository = snapshot.dependency_repository(declaration)
        if repository is not None and entry.matches_repository(repository):
            return declaration
    return None


def _row(name: str, head: str, release: str | None, change: str | None) -> str:
    release_cells = (
        f"<td>{release}</td><td>{change}</td>" if release is not None else ""
    )
    return f"<tr><td>{name}</td><td>{head}</td>{release_cells}</tr>\n"


def _plain(version: str | None) -> str:
    return f"<span class='mono'>{e(version)}</span>" if version else _MUTED_DASH


def _change(head: str | None, release: str | None) -> str:
    if head == release:
        return _MUTED_DASH
    if release is None:
        return '<span class="badge green">added</span>'
    if head is None:
        return '<span class="badge red">removed</span>'
    return '<span class="badge yellow">changed</span>'


def _dependency_name(
    declaration: DependencyDeclaration, snapshot: RepoSnapshot, site_root: str
) -> str:
    name = f"<span class='mono'>{e(declaration.module)}</span>"
    repository = snapshot.dependency_repository(declaration)
    if repository is None:
        return name
    source = _collected(snapshot, repository)
    if source is not None:
        return f"{name} {_repository_link(source, snapshot, site_root)}"
    return (
        f'{name} <a class="text-muted" href="https://github.com/{e(repository)}" '
        f'target="_blank" rel="noopener">{e(repository)} ↗</a>'
    )


def _repository_link(repo: RepoEntry, snapshot: RepoSnapshot, site_root: str) -> str:
    return (
        f'<a href="{e(site_root + repo.detail_path(snapshot.org_name))}">'
        f"{e(repo.full_name)}</a>"
    )


def _collected(snapshot: RepoSnapshot, repository: str) -> RepoEntry | None:
    return next((r for r in snapshot.repos if r.matches_repository(repository)), None)


def _usage(declaration: DependencyDeclaration | None, snapshot: RepoSnapshot) -> str:
    """Render the pin Bazel builds and how fresh it is."""
    if declaration is None:
        return _MUTED_DASH
    version = e(declaration.display_version)
    if declaration.pinned_revision is None:
        kind = declaration.override.value if declaration.override else "override"
        return (
            f"<span class='mono'>{version}</span> "
            f'<span class="badge muted">{e(kind.replace("_", " "))}</span>'
        )
    repository = snapshot.dependency_repository(declaration)
    resolution = snapshot.dependency_resolution(declaration)
    if repository is None or resolution is None:
        return f"<span class='mono'>{version}</span>"
    if resolution.resolved_sha is None:
        return (
            f"<span class='mono'>{version}</span> "
            '<span class="badge red" title="No matching commit, tag, or branch">'
            "unresolved</span>"
        )

    pin = (
        f'<a class="mono" href="https://github.com/{e(repository)}/commit/'
        f'{e(resolution.resolved_sha)}" target="_blank" rel="noopener" '
        f'title="{e(resolution.resolved_sha)}">{version}</a>'
    )
    release = _release_badge(
        resolution.latest_release, resolution.behind_latest_release_by
    )
    branch = _branch_badge(
        repository,
        snapshot,
        resolution.resolved_sha,
        resolution.ahead_of_default_branch_by,
        resolution.behind_default_branch_by,
    )
    return f"{pin} {release} {branch}"


def _release_badge(latest_release: str | None, behind: int | None) -> str:
    if latest_release is None:
        return '<span class="badge muted">no release</span>'
    if behind is None:
        return (
            f'<span class="badge muted" title="No common history with '
            f'{e(latest_release)}">release not comparable</span>'
        )
    if behind == 0:
        return f'<span class="badge green" title="Contains {e(latest_release)}">latest release</span>'
    return (
        f'<span class="badge yellow" title="{behind} commits of {e(latest_release)} '
        f'are missing">{e(latest_release)} available</span>'
    )


def _branch_badge(
    repository: str,
    snapshot: RepoSnapshot,
    sha: str,
    ahead: int | None,
    behind: int | None,
) -> str:
    source = _collected(snapshot, repository)
    branch = source.default_branch if source and source.default_branch else None
    if branch is None or ahead is None or behind is None:
        return '<span class="badge muted">branch not comparable</span>'
    compare_url = e(f"https://github.com/{repository}/compare/{sha}...{branch}")
    if ahead:
        return (
            f'<a class="badge red" href="{compare_url}" target="_blank" rel="noopener" '
            f'title="{ahead} commits are not on {e(branch)}">diverged from {e(branch)}</a>'
        )
    if behind == 0:
        return f'<span class="badge green">at {e(branch)}</span>'
    return (
        f'<a class="badge yellow" href="{compare_url}" target="_blank" rel="noopener">'
        f"{behind} behind {e(branch)}</a>"
    )
